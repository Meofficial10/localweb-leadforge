"""Demo-data detection + clearing.

Sample data seeded via `python -m scripts.reset_db --seed` is tagged with
source_place_id starting \"seed-\". These helpers let the UI show an
unmissable DEMO DATA badge and a one-click Clear demo data action.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.call import Call
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.core.integrations import LLM_PROVIDERS, VOICE_PROVIDERS, cfg as _icfg, provider_for as _iprovider_for


def _seed_lead_ids(db: Session) -> list[str]:
    rows = db.query(Lead.id).filter(Lead.source_place_id.like("seed-%")).all()
    return [r[0] for r in rows]


def demo_data_status(db: Session) -> dict:
    """Count present demo rows (empty = no demo data)."""
    ids = _seed_lead_ids(db)
    cam_ids = db.query(Campaign.id).filter(Campaign.name.like("Demo%")).all()
    campaigns = len(cam_ids)
    leads = len(ids)
    drafts = 0
    calls = 0
    if ids:
        drafts = db.query(Message.id).filter(Message.lead_id.in_(ids)).count()
        calls = db.query(Call.id).filter(Call.lead_id.in_(ids)).count()
    present = campaigns > 0 or leads > 0 or drafts > 0 or calls > 0
    return {
        "present": present,
        "campaigns": campaigns,
        "leads": leads,
        "drafts": drafts,
        "calls": calls,
        "integrations": 0,
        "message": "Demo data is present (seeded campaign, leads, drafts and/or calls). Nothing here is real.",
    }


def clear_demo_data(db: Session) -> dict:
    """Delete all seeded/demo rows. Returns what was removed."""
    ids = _seed_lead_ids(db)
    removed = {"campaigns": 0, "leads": 0, "drafts": 0, "calls": 0}
    if ids:
        removed["leads"] = len(ids)
        removed["drafts"] = db.query(Message).filter(Message.lead_id.in_(ids)).delete(synchronize_session=False)
        removed["calls"] = db.query(Call).filter(Call.lead_id.in_(ids)).delete(synchronize_session=False)
        db.query(Lead).filter(Lead.id.in_(ids)).delete(synchronize_session=False)
    # demo campaign(s)
    camps = db.query(Campaign).filter(Campaign.name.like("Demo%")).all()
    if camps:
        for c in camps:
            db.delete(c)
        removed["campaigns"] = len(camps)
    db.commit()
    return removed


def is_demo_lead(contact_value_domain):
    return False