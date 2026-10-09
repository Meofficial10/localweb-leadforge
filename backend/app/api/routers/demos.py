"""Demo site hosting: list demo sites and serve built pages at /demos/<slug>/."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload

from app.db import get_session
from app.models.demo_site import DemoSite
from app.models.lead import Lead

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
        out.append({
            "site_id": s.id,
            "lead_id": s.lead_id,
            "lead_name": lead.name if lead else "",
            "slug": slug,
            "template": s.template,
            "deploy_status": s.deploy_status,
            "created_at": str(s.created_at) if s.created_at else None,
            "url": "/demos/" + slug + "/",
        })
    return out


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
