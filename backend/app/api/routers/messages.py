"""Message approval + list with server-side pagination/filtering (M5)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.message import Message

router = APIRouter(prefix="/messages", tags=["messages"])


def serialize_msg(m: Message) -> dict:
    return {
        "id": m.id, "lead_id": m.lead_id, "channel": m.channel, "direction": m.direction,
        "sequence_step": m.sequence_step, "subject": m.subject, "status": m.status,
        "intent": m.intent, "created_at": str(m.created_at) if m.created_at else None,
    }


@router.get("")
def list_messages(
    status: str | None = None,
    channel: str | None = None,
    lead_id: str | None = None,
    q: str | None = None,
    page: int | None = None,
    page_size: int = 25,
    db: Session = Depends(get_session),
):
    """List messages with optional filters and pagination (M5).

    Backwards compatible: without `page`, returns a flat list (legacy).
    With `page`, returns a paginated envelope for the queue/inbox tables.
    """
    query = db.query(Message)
    if status:
        query = query.filter(Message.status == status)
    if channel:
        query = query.filter(Message.channel == channel)
    if lead_id:
        query = query.filter(Message.lead_id == lead_id)
    if q:
        query = query.filter(Message.subject.ilike("%" + q + "%") | Message.body.ilike("%" + q + "%"))
    query = query.order_by(Message.created_at.desc())
    if page is None:
        return [serialize_msg(m) for m in query.all()]
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    total = query.count()
    items = [serialize_msg(m) for m in query.offset((page - 1) * page_size).limit(page_size).all()]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.post("/{message_id}/approve")
def approve_message(message_id: str, db: Session = Depends(get_session)):
    msg = db.get(Message, message_id)
    if not msg:
        raise HTTPException(404, "message not found")
    if msg.status != "draft":
        raise HTTPException(400, "only drafts can be approved")
    msg.status = "approved"
    db.commit()
    return serialize_msg(msg)
