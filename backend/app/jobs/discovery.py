"""DISCOVER stage: query all configured sources, filter to no-website places,
dedupe by (source, source_place_id), and insert leads. Idempotent: re-running a
campaign run never creates duplicate leads.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.sources.base import SourceAdapter
from app.sources.overpass import OverpassAdapter
from app.sources.places import GooglePlacesAdapter
from app.utils import new_uuid

DISCOVER_STAGE = "discover"


def discover_campaign(db: Session, campaign: Campaign, adapters: list[SourceAdapter] | None = None) -> dict:
    """Run discovery for a campaign. Returns {found, inserted, no_website, deduped}."""
    if adapters is None:
        adapters = [GooglePlacesAdapter(), OverpassAdapter()]
    results = {"found": 0, "no_website": 0, "inserted": 0}
    seen: set[tuple[str, str]] = set()  # dedupe within this run (session may be autoflush=False)
    for adapter in adapters:
        for cat in campaign.categories or []:
            found = adapter.search(campaign.city, [cat])
            for place in found:
                results["found"] += 1
                # DISCOVER filter: keep only places with an EMPTY website field
                if place.website:
                    continue
                results["no_website"] += 1
                key = (place.source, place.source_place_id)
                if key in seen:
                    continue
                seen.add(key)
                # dedupe against committed rows from earlier runs
                existing = db.execute(
                    select(Lead).where(
                        Lead.source == place.source,
                        Lead.source_place_id == place.source_place_id,
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    continue
                lead = Lead(
                    id=new_uuid(),
                    campaign_id=campaign.id,
                    source=place.source,
                    source_place_id=place.source_place_id,
                    name=place.name,
                    category=place.category,
                    address=place.address,
                    lat=place.lat,
                    lng=place.lng,
                    rating=place.rating,
                    review_count=place.review_count,
                    has_website=False,
                    status="discovered",
                )
                db.add(lead)
                results["inserted"] += 1
    db.commit()
    record(db, action="discovery_run", lead_id=None,
           detail={"campaign_id": campaign.id, "results": results})
    return results
