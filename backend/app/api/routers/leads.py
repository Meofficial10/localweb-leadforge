"""Lead list/detail, demo regenerate, data deletion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.jobs.build_demo import build_demo
from app.models.lead import Lead

router = APIRouter(prefix="/leads", tags=["leads"])


def serialize_lead(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "campaign_id": lead.campaign_id,
        "source": lead.source,
        "source_place_id": lead.source_place_id,
        "name": lead.name,
        "category": lead.category,
        "address": lead.address,
        "rating": float(lead.rating) if lead.rating is not None else None,
        "review_count": lead.review_count,
        "contact_type": lead.contact_type,
        "status": lead.status,
        "created_at": str(lead.created_at),
        "contacts": [{"kind": c.kind, "value": c.value, "source_url": c.source_url} for c in lead.contacts],
        "demo": [{"preview_url": d.preview_url, "template": d.template, "deploy_status": d.deploy_status}
                 for d in lead.demo_sites] or None,
    }


@router.get("")
def list_leads(status: str | None = None, contact_type: str | None = None,
               campaign_id: str | None = None, limit: int = 100,
               db: Session = Depends(get_session)):
    q = db.query(Lead)
    if status:
        q = q.filter(Lead.status == status)
    if contact_type:
        q = q.filter(Lead.contact_type == contact_type)
    if campaign_id:
        q = q.filter(Lead.campaign_id == campaign_id)
    q = q.limit(min(limit, 500))
    return [serialize_lead(l) for l in q.all()]


@router.get("/{lead_id}")
def lead_detail(lead_id: str, db: Session = Depends(get_session)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    data = serialize_lead(lead)
    if lead.profile:
        data["profile"] = {
            "summary": lead.profile.summary,
            "services": lead.profile.services,
            "tone": lead.profile.tone,
            "selling_points": lead.profile.selling_points,
            "brand": lead.profile.brand,
        }
    data["messages"] = [
        {"id": m.id, "subject": m.subject, "status": m.status, "sequence_step": m.sequence_step}
        for m in lead.messages
    ]
    data["calls"] = [
        {"id": c.id, "outcome": c.outcome, "transcript": c.transcript, "recording_consent": c.recording_consent}
        for c in lead.calls
    ]
    return data


@router.post("/{lead_id}/demo/regenerate")
def regenerate_demo(lead_id: str, db: Session = Depends(get_session)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    site = build_demo(db, lead)
    return {"preview_url": site.preview_url if site else None, "status": "regenerated" if site else "failed"}


@router.delete("/{lead_id}")
def delete_lead(lead_id: str, db: Session = Depends(get_session)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    db.delete(lead)
    db.commit()
    return {"deleted": True}
