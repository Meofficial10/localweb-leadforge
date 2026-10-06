"""ENRICH job runner: enrich all leads in "discovered" state for a campaign."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enrichment.service import EnrichmentService
from app.models.campaign import Campaign
from app.models.lead import Lead


def run_enrichment_for_campaign(db: Session, campaign: Campaign, service: EnrichmentService | None = None) -> dict:
    service = service or EnrichmentService()
    leads = db.execute(
        select(Lead).where(Lead.campaign_id == campaign.id, Lead.status == "discovered")
    ).scalars().all()
    results = {"enriched": 0, "no_contact": 0, "failed": 0}
    for lead in leads:
        try:
            r = service.enrich(db, lead)
            if r.get("classification") in ("email", "phone", "both"):
                results["enriched"] += 1
            else:
                results["no_contact"] += 1
        except Exception:  # noqa: BLE001
            results["failed"] += 1
    return results
