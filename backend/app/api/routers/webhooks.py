"""Webhook endpoints for email and voice providers."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.state_machine import transition
from app.core.settings_service import get_setting, set_setting
from app.core.suppression import SuppressionService
from app.db import get_session
from app.models.lead import Lead
from app.models.message import Message
from app.models.contact import Contact
from app.utils import new_uuid

router = APIRouter(prefix='/webhooks', tags=['webhooks'])


class EmailEvent(BaseModel):
    event: str  # bounce | open | reply | unsubscribe
    email: str
    message_id: str = ''
    body: str = ''


def _get_lead_by_email(db: Session, email: str) -> Lead | None:
    res = db.execute(
        select(Contact).where(Contact.kind == 'email', Contact.value == email.lower())
    ).scalars().first()
    if res is None:
        return None
    return db.get(Lead, res.lead_id)


@router.post('/email')
def email_event(payload: EmailEvent, db: Session = Depends(get_session)):
    lead = _get_lead_by_email(db, payload.email)
    if payload.event == 'unsubscribe':
        svc = SuppressionService(db)
        svc.add('email', payload.email.lower(), reason='unsubscribe')
        svc.add('domain', payload.email.split('@')[-1].lower(), reason='unsubscribe')
        if lead:
            lead.status = transition(lead.status, 'opted_out')
            db.commit()
        record(db, action='unsubscribe', lead_id=lead.id if lead else None,
               detail={'email': payload.email})
        return {'handled': True, 'action': 'suppressed'}
    if payload.event == 'bounce':
        msg = db.get(Message, payload.message_id) if payload.message_id else None
        if msg:
            msg.bounced = True
            msg.status = 'bounced'
            if lead:
                lead.status = transition(lead.status, 'bounced')
            db.commit()
            _update_auto_pause_stats(db, bounced=True)
        record(db, action='bounce', lead_id=lead.id if lead else None,
               detail={'email': payload.email})
        return {'handled': True, 'action': 'bounced'}
    if payload.event == 'open':
        msg = db.get(Message, payload.message_id) if payload.message_id else None
        if msg:
            msg.opened_at = datetime.now()
            db.commit()
        return {'handled': True}
    if payload.event == 'reply':
        intent = _classify_intent(payload.body or '')
        # link the inbound reply to the outbound message so the UI can thread them
        parent = db.get(Message, payload.message_id) if payload.message_id else None
        inbound = Message(
            id=new_uuid(),
            lead_id=lead.id if lead else (parent.lead_id if parent else None),
            channel='email',
            direction='inbound',
            sequence_step=(parent.sequence_step if parent else 1),
            subject=('Re: ' + parent.subject) if parent else None,
            inbound_content=payload.body or '(no body)',
            status='replied',
            provider_message_id=payload.message_id or '',
            intent=intent,
            handled=False,
        )
        db.add(inbound)
        if lead:
            lead.status = transition(lead.status, 'replied')
        if parent:
            parent.status = 'replied'
        db.commit()
        record(db, action='reply', lead_id=lead.id if lead else None,
               detail={'email': payload.email, 'intent': intent})
        return {'handled': True, 'action': 'replied', 'intent': intent}
    return {'handled': False}


def _classify_intent(body: str) -> str:
    b = body.lower()
    if any(k in b for k in ['unsubscribe', 'stop', 'opt out', 'opt-out', 'remove']):
        return 'opt_out'
    if b.strip() == '' or len(b) < 3:
        return 'neutral'
    if any(k in b for k in ['?', 'cost', 'price', 'how much', 'tell me more', 'details', 'demo']):
        return 'question'
    if any(k in b for k in ['no thanks', 'not interested', 'don''t want', "don't want", 'no thank']):
        return 'not_interested'
    if any(k in b for k in ['yes', 'interested', 'sure', 'ok', 'send', 'great', 'book', 'schedule']):
        return 'interested'
    return 'neutral'


def _update_auto_pause_stats(db: Session, bounced: bool = False) -> None:
    total = int(get_setting(db, 'stats.total_messages', 0) or 0)
    bounces = int(get_setting(db, 'stats.bounces', 0) or 0)
    total += 1
    if bounced:
        bounces += 1
    set_setting(db, 'stats.total_messages', total)
    set_setting(db, 'stats.bounces', bounces)
    set_setting(db, 'stats.bounce_rate', round(bounces / max(total, 1), 4))


@router.post('/voice')
async def voice_event(payload: dict, db: Session = Depends(get_session)):
    record(db, action='voice_webhook', lead_id=None, detail={'body': payload})
    return {'handled': True}