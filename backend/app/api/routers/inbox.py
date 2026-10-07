"""Inbox: inbound replies with intent labels, handled flag, take-over."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.audit import record
from app.db import get_session
from app.models.lead import Lead
from app.models.message import Message

router = APIRouter(prefix='/inbox', tags=['inbox'])


def _serialize(db: Session, m: Message) -> dict:
    lead = db.get(Lead, m.lead_id) if m.lead_id else None
    return {
        'id': m.id,
        'lead_id': m.lead_id,
        'lead_name': lead.name if lead else '?',
        'lead_email': (lead.contacts[0].value if lead and lead.contacts and lead.contacts[0].kind == 'email' else None) if lead else None,
        'subject': m.subject,
        'content': m.inbound_content or m.body,
        'intent': m.intent or 'neutral',
        'handled': m.handled,
        'status': m.status,
        'received_at': str(m.created_at) if getattr(m, 'created_at', None) else None,
    }


@router.get('')
def list_inbox(scope: str = 'unhandled', db: Session = Depends(get_session)):
    """List inbound replies. scope: unhandled | handled | all."""
    q = db.query(Message).filter(Message.direction == 'inbound')
    if scope == 'unhandled':
        q = q.filter(Message.handled == False)  # noqa: E712
    elif scope == 'handled':
        q = q.filter(Message.handled == True)  # noqa: E712
    q = q.order_by(Message.created_at.desc()).limit(300)
    return [_serialize(db, m) for m in q.all()]


@router.post('/{message_id}/handle')
def mark_handled(message_id: str, db: Session = Depends(get_session)):
    m = db.get(Message, message_id)
    if not m:
        raise HTTPException(404, 'message not found')
    m.handled = True
    m.status = 'handled'
    db.commit()
    record(db, action='inbox_handled', lead_id=m.lead_id, detail={'message_id': m.id})
    return _serialize(db, m)


@router.post('/{message_id}/take-over')
def take_over(message_id: str, db: Session = Depends(get_session)):
    """Mark that a human has taken over this thread."""
    m = db.get(Message, message_id)
    if not m:
        raise HTTPException(404, 'message not found')
    m.handled = True
    m.status = 'handled'
    db.commit()
    record(db, action='inbox_take_over', lead_id=m.lead_id, detail={'message_id': m.id})
    return _serialize(db, m)