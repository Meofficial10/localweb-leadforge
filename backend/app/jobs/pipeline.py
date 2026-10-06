"""Pipeline runner tying independent stages together for a campaign.

Each stage is retryable and isolated: a failure in one lead never blocks the others.
Stage order: discover -> enrich -> profile -> build(demo) -> draft -> send -> followup / call.
Outbound stages respect the compliance gate, so in dry-run nothing leaves the box.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jobs.discovery import discover_campaign
from app.jobs.enrichment import run_enrichment_for_campaign
from app.jobs.build_demo import build_demo
from app.jobs.profile import build_profile
from app.jobs.send import prepare_email_message, schedule_followup
from app.jobs.voice import place_call_for_lead
from app.models.campaign import Campaign
from app.models.lead import Lead


def run_campaign_once(db: Session, campaign: Campaign, *,
                      discover: bool = True, enrich: bool = True, build: bool = True,
                      max_leads: int | None = None) -> dict[str, Any]:
    """Advance every lead one step along the pipeline."""
    summary: dict[str, Any] = {
        "discovered": 0, "enriched": 0, "profiled": 0, "demo_built": 0,
        "queued_email": 0, "contacted_call": 0, "failed": [],
    }
    if discover:
        d = discover_campaign(db, campaign)
        summary["discovered"] = d.get("inserted", 0)
    if enrich:
        r = run_enrichment_for_campaign(db, campaign)
        summary["enriched"] = r["enriched"]

    leads = db.execute(
        select(Lead).where(Lead.campaign_id == campaign.id)
    ).scalars().all()

    for lead in leads:
        try:
            if lead.status == "enriched":
                if lead.profile is None and build:
                    build_profile(db, lead)
                    summary["profiled"] += 1
            elif lead.status == "profiled":
                if build:
                    site = build_demo(db, lead)
                    if site is not None:
                        summary["demo_built"] += 1
            elif lead.status == "demo_ready":
                if lead.demo_sites:
                    msg = prepare_email_message(db, lead, campaign)
                    if msg is not None:
                        summary["queued_email"] += 1
            elif lead.status == "contacted":
                schedule_followup(db, lead, campaign)
        except Exception as exc:  # noqa: BLE001
            summary["failed"].append({"lead": lead.id, "err": str(exc)})
    return summary
