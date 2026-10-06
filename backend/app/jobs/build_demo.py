"""BUILD DEMO stage: LLM generates a responsive one-page HTML site from the profile
using the template library, deploys it, and stores the preview URL."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.build.deploy import DeployAdapter, LocalDeploy
from app.build.templates import render_demo_site
from app.core.audit import record
from app.core.state_machine import transition
from app.jobs.profile import build_profile
from app.models.demo_site import DemoSite
from app.models.lead import Lead
from app.utils import new_uuid


def build_demo(db: Session, lead: Lead, deploy: DeployAdapter | None = None) -> DemoSite | None:
    # ensure a profile exists
    if lead.profile is None:
        try:
            build_profile(db, lead)
        except Exception:  # noqa: BLE001
            return None
    profile = lead.profile
    data = {
        "summary": profile.summary or "",
        "services": profile.services or [],
        "tone": profile.tone or "",
        "selling_points": profile.selling_points or [],
        "brand": profile.brand or {},
    }
    business = {
        "name": lead.name,
        "address": lead.address,
        "category": lead.category,
        "phone": lead.contacts[0].value if (lead.contacts and lead.contacts[0].kind == "phone") else None,
    }
    sender = "demo@leads.example.com"
    html = render_demo_site(data, business, sender)

    deploy = deploy or LocalDeploy()
    site_name = f"{lead.name.strip().lower().replace(' ', '-')}-{lead.source_place_id[-8:]}"
    result = deploy.deploy(lead_id=lead.id, html=html, site_name=site_name)

    site = DemoSite(
        id=new_uuid(),
        lead_id=lead.id,
        template=(data["brand"] or {}).get("theme", "fresh"),
        html_path=result.html_path,
        preview_url=result.preview_url,
        deploy_status="live",
    )
    db.add(site)
    lead.status = transition(lead.status, "demo_ready")
    db.commit()
    record(db, action="demo_built", lead_id=lead.id, detail={"preview_url": result.preview_url})
    return site
