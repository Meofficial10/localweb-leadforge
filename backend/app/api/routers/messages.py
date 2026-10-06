"""Message approval + list."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.message import Message

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("")
def list_messages(status: str | None = None, db: Session = Depends(get_session)):
    q = db.query(Message)
    if status:
        q = q.filter(Message.status == status)
    return q.all()


@router.post("/{message_id}/approve")
def approve_message(message_id: str, db: Session = Depends(get_session)):
    msg = db.get(Message, message_id)
    if not msg:
        raise HTTPException(404, "message not found")
    if msg.status != "draft":
        raise HTTPException(400, f"only drafts can be approved (status={msg.status})")
    msg.status = "approved"
    db.commit()
    return msg
