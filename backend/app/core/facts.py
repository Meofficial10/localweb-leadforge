"""Collect a lead's *verified facts* into rows (Workstream B).

Only facts that originate from a legitimate source (OSM discovery fields,
enrichment results with source URL, or explicit human entry) become verified
facts. Generated copy (Profile.summary etc.) is NEVER written back as a fact.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.lead import Lead
from app.models.verified_fact import VerifiedFact


def _upsert(db: Session, lead_id: str, field: str, value: str | None,
            source: str | None, is_null_fact: bool = False) -> None:
    if value is None:
        return
    existing = db.execute(
        select(VerifiedFact).where(
            VerifiedFact.lead_id == lead_id,
            VerifiedFact.field == field,
            VerifiedFact.value == str(value),
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(VerifiedFact(
            lead_id=lead_id, field=field, value=str(value),
            source=source, is_null_fact=bool(is_null_fact),
        ))


def collect_verified_facts(db: Session, lead: Lead) -> list[VerifiedFact]:
    """Build VerifiedFact rows from the lead record + its contacts. Idempotent."""
    _upsert(db, lead.id, "name", lead.name, "OSM discovery")
    _upsert(db, lead.id, "category", lead.category, "OSM discovery")
    _upsert(db, lead.id, "address", lead.address, "OSM discovery")
    if lead.lat is not None and lead.lng is not None:
        _upsert(db, lead.id, "coordinates", f"{lead.lat:.5f},{lead.lng:.5f}", "OSM discovery")
    if lead.rating is not None:
        _upsert(db, lead.id, "rating", str(lead.rating), "OSM discovery")
    if lead.review_count is not None:
        _upsert(db, lead.id, "review_count", str(lead.review_count), "OSM discovery")
    # website == none when discovery found no website
    if not lead.has_website:
        _upsert(db, lead.id, "website", "none", "OSM discovery (no website found)", is_null_fact=True)
    elif lead.raw_website:
        _upsert(db, lead.id, "website", lead.raw_website, "OSM discovery")
    for c in lead.contacts:
        field = "phone" if c.kind == "phone" else ("email" if c.kind == "email" else ("website" if c.kind == "website" else c.kind))
        _upsert(db, lead.id, field, c.value, c.source_url or "enrichment", is_null_fact=False)
    try:
        db.commit()
    except Exception:
        db.rollback()
    return db.execute(
        select(VerifiedFact).where(VerifiedFact.lead_id == lead.id).order_by(VerifiedFact.field)
    ).scalars().all()


def facts_dict(facts: list[dict]) -> dict:
    out = {}
    for it in facts:
        f = it.get("field"); v = it.get("value")
        out.setdefault(f, []).append(str(v))
    return out


def facts_to_prompt_block(facts: list[dict]) -> str:
    """Render verified facts into a prompt block: one field per line with source."""
    lines = []
    for it in (facts or []):
        nulls = " (absent)" if it.get("is_null_fact") else ""
        src = it.get("source") or ""
        lines.append(f"- {it['field']}: {it['value']} [source: {src}]{nulls}")
    return "\n".join(lines) if lines else "(no verified facts available)"
