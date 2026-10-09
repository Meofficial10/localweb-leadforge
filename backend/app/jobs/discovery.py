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


def _adapters_for(db: Session, campaign: Campaign):
    chosen = getattr(campaign, "lead_sources", None) or []
    if not chosen:
        legacy = campaign.lead_source or "both"
        chosen = ["google", "osm"] if legacy == "both" else [legacy]
    radius_m = (campaign.area_radius_km or 3.0) * 1000.0
    adapters = []
    for src in chosen:
        if src == "google":
            adapters.append(GooglePlacesAdapter())
        elif src == "osm":
            adapters.append(OverpassAdapter())
        elif src == "apify":
            from app.sources.apify import ApifyAdapter
            adapters.append(ApifyAdapter(db=db, campaign_id=campaign.id))
    return adapters, radius_m


def discover_campaign(db: Session, campaign: Campaign, adapters=None, radius_m: float = 3000.0) -> dict:
    if adapters is None:
        adapters, radius_m = _adapters_for(db, campaign)
    adapters = [a for a in adapters if a is not None]
    results = {"found": 0, "with_website": 0, "without_website": 0,
               "with_phone": 0, "with_email": 0, "inserted": 0, "deduped": 0}
    per_source = []
    samples = []
    reasons = []
    seen = set()
    for adapter in adapters:
        src_status = {"source": getattr(adapter, "name", "?")}
        src_found = 0
        src_places = []
        for cat in campaign.categories or []:
            try:
                found = adapter.search(campaign.city, [cat], country=campaign.country or "Singapore",
                                       radius_m=radius_m)
            except TypeError:
                found = adapter.search(campaign.city, [cat])
            except Exception as e:
                src_status["error"] = "%s: %s" % (type(e).__name__, e)
                continue
            src_found += len(found)
            src_places.extend(found)
        st = getattr(adapter, "last_status", None) or {}
        src_status.update({k: v for k, v in st.items() if k != "source"})
        src_status["found"] = src_found
        if not src_found and not src_status.get("error"):
            reasons.append(src_status["source"] + ": returned no results for this run.")
        elif src_status.get("error"):
            reasons.append(src_status["source"] + ": " + src_status["error"])
        per_source.append(src_status)
        for place in src_places:
            results["found"] += 1
            w = bool(place.website)
            results["with_website" if w else "without_website"] += 1
            if place.phone:
                results["with_phone"] += 1
            if place.email:
                results["with_email"] += 1
            if w:
                continue
            key = (place.source, place.source_place_id)
            if key in seen:
                results["deduped"] += 1
                continue
            seen.add(key)
            existing = db.execute(select(Lead).where(
                Lead.source == place.source, Lead.source_place_id == place.source_place_id,
            )).scalar_one_or_none()
            if existing is not None:
                results["deduped"] += 1
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
            if len(samples) < 5:
                samples.append({
                    "name": place.name, "category": place.category,
                    "source": place.source, "source_place_id": place.source_place_id,
                    "lat": place.lat, "lng": place.lng,
                    "website": place.website, "phone": place.phone, "email": place.email,
                })
    if results["inserted"] == 0 and results["found"] == 0:
        base = "No leads found in this run."
        results["reason"] = base + (" " + " | ".join(reasons) if reasons else " Check that a lead source is configured and the category/area yields businesses.")
    elif results["inserted"] == 0:
        results["reason"] = "Found %d place(s) but all had a website or were already known - no new no-website leads to insert." % results["found"]
    else:
        results["reason"] = None
    results["no_website"] = results["without_website"]  # backward-compat alias
    results["per_source"] = per_source
    results["samples"] = samples
    db.commit()
    record(db, action="discovery_run", lead_id=None,
           detail={"campaign_id": campaign.id, "results": results})
    return results
