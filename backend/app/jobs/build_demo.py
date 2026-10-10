"""BUILD DEMO stage: render a grounded, per-lead one-page HTML demo site using the
same template library as Workstream C (8 theme packs), deploy it locally, and
store the preview URL. Only verified contact data and verified/generic copy are
placed on the page; sender identity is the configured one (never a placeholder).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.build.deploy import DeployAdapter, LocalDeploy
from app.build.templates import render_demo_site, theme_for_category
from app.config import settings
from app.core.audit import record
from app.core.facts import collect_verified_facts
from app.core.state_machine import transition
from app.jobs.profile import build_profile
from app.models.demo_site import DemoSite
from app.models.lead import Lead
from app.models.verified_fact import VerifiedFact
from app.utils import new_uuid


def _fact_value(facts: list[VerifiedFact], field: str) -> str | None:
    for f in facts:
        if f.field == field and not f.is_null_fact:
            return f.value
    return None


def _contacts_map(lead: Lead) -> dict[str, str]:
    out = {}
    for c in (lead.contacts or []):
        if c.kind in ("phone", "email", "website") and c.kind not in out:
            out[c.kind] = c.value
    return out


def build_demo(db: Session, lead: Lead, deploy: DeployAdapter | None = None,
               template: str | None = None) -> DemoSite | None:
    if template is None:
        prev = (db.query(DemoSite).filter(DemoSite.lead_id == lead.id)
                .order_by(DemoSite.created_at.desc()).first())
        if prev is not None and prev.template:
            template = prev.template
    if lead.profile is None:
        try:
            build_profile(db, lead)
        except Exception:  # noqa: BLE001
            return None
    profile = lead.profile
    facts = collect_verified_facts(db, lead)
    facts_dicts = [{"id": f.id, "field": f.field, "value": f.value, "source": f.source,
                    "is_null_fact": f.is_null_fact} for f in facts]

    contacts = _contacts_map(lead)
    phone = _fact_value(facts, "phone") or contacts.get("phone") or ""
    email = _fact_value(facts, "email") or contacts.get("email") or ""
    opening_hours = _fact_value(facts, "opening_hours") or ""

    data = {
        "summary": profile.summary or "",
        "services": [
            {"text": s, "kind": "generic", "source_fact_id": None}
            for s in (profile.services or [])
        ],
        "tone": profile.tone or "",
        "selling_points": [
            {"text": s, "kind": "generic", "source_fact_id": None}
            for s in (profile.selling_points or [])
        ],
        "brand": profile.brand or {},
        "opening_hours": opening_hours,
    }
    business = {
        "name": lead.name,
        "address": lead.address,
        "category": lead.category,
        "phone": phone,
        "email": email,
        "whatsapp": phone,
    }
    sender = settings.sender_name or ""
    if settings.sender_email and "example" not in (settings.sender_email or ""):
        sender = settings.sender_email
    html = render_demo_site(data, business, sender, theme_override=template)

    deploy = deploy or LocalDeploy()
    site_name = f"{lead.name.strip().lower().replace(' ', '-')}-{lead.source_place_id[-8:]}"
    site_name = site_name.replace("--", "-").strip("-")
    result = deploy.deploy(lead_id=lead.id, html=html, site_name=site_name)

    site = DemoSite(
        id=new_uuid(),
        lead_id=lead.id,
        template=(template or theme_for_category(lead.category)),
        html_path=result.html_path,
        preview_url=result.preview_url,
        deploy_status="live",
    )
    db.add(site)
    if lead.status != "demo_ready":
        lead.status = transition(lead.status, "demo_ready")
    db.commit()
    record(db, action="demo_built", lead_id=lead.id,
           detail={"preview_url": result.preview_url, "theme": site.template,
                   "facts_used": len(facts_dicts)})
    return site
