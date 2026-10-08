"""Lead list/detail, demo regenerate, data deletion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.jobs.build_demo import build_demo
from app.models.lead import Lead

router = APIRouter(prefix="/leads", tags=["leads"])


def serialize_lead(lead: Lead) -> dict:
    profile = lead.profile
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
        "is_demo": lead.source_place_id.startswith("seed-"),
        "created_at": str(lead.created_at),
        "contacts": [{"kind": c.kind, "value": c.value, "source_url": c.source_url} for c in lead.contacts],
        "demo": [{"preview_url": d.preview_url, "template": d.template, "deploy_status": d.deploy_status}
                 for d in lead.demo_sites] or None,
        "profile": {
            "summary": profile.summary,
            "services": profile.services or [],
            "tone": profile.tone,
            "selling_points": profile.selling_points or [],
            "brand": profile.brand or {},
        } if profile else None,
        "messages": [{
            "id": m.id, "channel": m.channel, "direction": m.direction,
            "subject": m.subject, "status": m.status, "sequence_step": m.sequence_step,
            "intent": m.intent, "created_at": str(m.created_at) if getattr(m, "created_at", None) else None,
        } for m in (lead.messages or [])],
        "calls": [{
            "id": c.id, "outcome": c.outcome, "duration_sec": c.duration_sec,
            "started_at": str(c.started_at) if c.started_at else None,
            "transcript": c.transcript, "recording_url": c.recording_url,
            "ai_disclosed": c.ai_disclosed, "dnc_checked_at": str(c.dnc_checked_at) if c.dnc_checked_at else None,
        } for c in (lead.calls or [])],
    }


@router.get("")
def list_leads(
    status: str | None = None,
    contact_type: str | None = None,
    campaign_id: str | None = None,
    category: str | None = None,
    search: str | None = None,
    sort: str | None = "-created_at",
    page: int = 1,
    page_size: int = 25,
    limit: int | None = None,
    db: Session = Depends(get_session),
):
    """List leads with filters, search, sort and pagination.

    Backwards-compatible: when `limit` is provided the legacy path is used
    (flat list, no pagination metadata); otherwise a paginated envelope.
    """
    q = db.query(Lead)
    if status:
        q = q.filter(Lead.status == status)
    if contact_type:
        q = q.filter(Lead.contact_type == contact_type)
    if campaign_id:
        q = q.filter(Lead.campaign_id == campaign_id)
    if category:
        q = q.filter(Lead.category.ilike("%" + category + "%"))
    if search:
        q = q.filter(
            Lead.name.ilike("%" + search + "%")
            | Lead.address.ilike("%" + search + "%")
            | Lead.category.ilike("%" + search + "%"),
        )
    columns = {
        "name": Lead.name,
        "rating": Lead.rating,
        "review_count": Lead.review_count,
        "category": Lead.category,
        "status": Lead.status,
        "created_at": Lead.created_at,
    }
    desc = bool(sort and sort.startswith("-"))
    key = sort[1:] if desc else (sort or "created_at")
    col = columns.get(key)
    if col is not None:
        q = q.order_by(col.desc() if desc else col.asc())
    if limit is not None:
        return [serialize_lead(l) for l in q.limit(min(limit, 500)).all()]
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    total = q.count()
    items = [serialize_lead(l) for l in q.offset((page - 1) * page_size).limit(page_size).all()]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{lead_id}")
def lead_detail(lead_id: str, db: Session = Depends(get_session)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "lead not found")
    # serialize_lead already includes profile, message timeline and calls
    return serialize_lead(lead)


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

@router.post("/bulk/delete")
def bulk_delete_leads(payload: dict, db: Session = Depends(get_session)):
    from app.core.audit import record
    ids = payload.get("ids") or []
    if not ids:
        return {"deleted": 0}
    deleted = 0
    for lid in ids:
        lead = db.get(Lead, lid)
        if lead:
            db.delete(lead)
            deleted += 1
    db.commit()
    if deleted:
        record(db, action="leads_bulk_delete", detail={"count": deleted})
    return {"deleted": deleted}


@router.post("/bulk/suppress")
def bulk_suppress_leads(payload: dict, db: Session = Depends(get_session)):
    from app.core.audit import record
    from app.core.suppression import add
    ids = payload.get("ids") or []
    reason = payload.get("reason") or "bulk suppression from console"
    if not ids:
        return {"suppressed": 0}
    suppressed = 0
    for lid in ids:
        lead = db.get(Lead, lid)
        if not lead:
            continue
        for c in lead.contacts:
            if add(db, "email", c.value, reason=reason):
                suppressed += 1
    db.commit()
    record(db, action="leads_bulk_suppress", detail={"count": suppressed, "reason": reason})
    return {"suppressed": suppressed}
