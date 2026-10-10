"""Demo site hosting: list demo sites and serve built pages at /demos/<slug>/."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from app.db import get_session
from app.models.demo_site import DemoSite
from app.models.lead import Lead

from app.build.templates import THEMES

THEME_KEYS = set(THEMES.keys())

router = APIRouter(prefix="/demos", tags=["demos"])


def _slug(lead: Lead) -> str:
    """Deterministic slug matching build_demo site_name, e.g. spa-2113ef44."""
    base = (lead.name or "").strip().lower().replace(" ", "-") or "lead"
    suffix = (lead.source_place_id or "")[-8:] or (str(lead.id)[:8])
    return base + "-" + suffix


def _fallback_slug(site: DemoSite) -> str:
    """Slug derived from the stored HTML path when the lead row is missing."""
    from pathlib import Path as P
    p = P(site.html_path or "")
    return (p.parent.name if p.parent and p.parent.name else site.lead_id)[:64]


@router.get("")
def list_demos(db: Session = Depends(get_session)):
    """Every demo site with a friendly slug and served URL (LEF side)."""
    rows = db.query(DemoSite).outerjoin(Lead, DemoSite.lead_id == Lead.id).order_by(DemoSite.created_at.desc()).all()
    out = []
    for s in rows:
        lead = s.lead
        slug = _slug(lead) if lead is not None else _fallback_slug(s)
        size_kb = None
        if s.html_path:
            try:
                sp = Path(s.html_path)
                size_kb = sp.stat().st_size if sp.exists() else None
            except Exception:
                size_kb = None
        out.append({
            "site_id": s.id,
            "lead_id": s.lead_id,
            "lead_name": lead.name if lead else "",
            "slug": slug,
            "template": s.template,
            "deploy_status": s.deploy_status,
            "created_at": str(s.created_at) if s.created_at else None,
            "url": "/demos/" + slug + "/",
            "size_kb": size_kb,
        })
    return out




@router.get("/themes")
def demo_themes():
    """Available theme packs for the demo picker."""
    from app.build.templates import all_themes
    return all_themes()


@router.post("/{lead_id}/delete")
def delete_demo_for_lead(lead_id: str, db: Session = Depends(get_session)):
    """Delete the demo site for a lead (removal request flow)."""
    rows = db.query(DemoSite).filter(DemoSite.lead_id == lead_id).all()
    if not rows:
        raise HTTPException(404, "No demo site for this lead")
    from app.core.audit import record as _record_audit
    for site in rows:
        _remove_site_files(site)
        db.delete(site)
    db.commit()
    _record_audit(db, action="demo_deleted", lead_id=lead_id, detail={"removal": "request"})
    return {"deleted": len(rows)}


@router.get("/{lead_id}/build_log")
def demo_build_log(lead_id: str, db: Session = Depends(get_session)):
    """Return the demo build log: facts used, deploy status, expiry."""
    site = db.query(DemoSite).filter(DemoSite.lead_id == lead_id).order_by(DemoSite.created_at.desc()).first()
    if not site:
        raise HTTPException(404, "no demo site")
    lead = db.get(Lead, site.lead_id)
    from app.core.facts import collect_verified_facts as _collect
    facts_list = []
    if lead:
        for f in _collect(db, lead):
            facts_list.append({"field": f.field, "value": f.value, "source": f.source})
    return {
        "site_id": site.id,
        "template": site.template,
        "version": site.version,
        "deploy_status": site.deploy_status,
        "created_at": str(site.created_at) if site.created_at else None,
        "preview_url": site.preview_url,
        "html_path": site.html_path,
        "facts": facts_list[:20],
        "expired": demo_expired(site),
    }


@router.patch("/{lead_id}/theme")
def update_demo_theme(lead_id: str, payload: dict, db: Session = Depends(get_session)):
    """Switch the theme for a lead's demo site and regenerate the HTML."""
    from app.jobs.build_demo import build_demo as _bd
    template = (payload or {}).get("template") or ""
    if template not in THEME_KEYS:
        raise HTTPException(400, "unknown theme")
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    site = _bd(db, lead, template=template)
    return {"template": template, "preview_url": site.preview_url if site else None, "regenerate": True}


@router.get("/{slug}")
def serve_demo(slug: str, db: Session = Depends(get_session)):
    """Serve an existing demo page by its friendly slug."""
    slug = slug.strip("/")
    site = None
    rows = db.query(DemoSite).outerjoin(Lead, DemoSite.lead_id == Lead.id).all()
    for row in rows:
        slug_candidate = _slug(row.lead) if row.lead is not None else _fallback_slug(row)
        if slug_candidate == slug:
            site = row
            break
    if site is None:
        raise HTTPException(status_code=404, detail="demo not found")
    if not site.html_path or not Path(site.html_path).exists():
        raise HTTPException(status_code=404, detail="demo file missing")
    return HTMLResponse(Path(site.html_path).read_text(encoding="utf-8"))


def demo_expired(site) -> bool:
    """A deployed demo auto-expires 30 days after creation."""
    from datetime import datetime, timedelta
    if not site.created_at:
        return False
    return datetime.now() - site.created_at >= timedelta(days=30)


def _remove_site_files(site) -> None:
    if site.html_path:
        from pathlib import Path
        p = Path(site.html_path)
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
