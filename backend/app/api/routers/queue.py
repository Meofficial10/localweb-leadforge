"""Outreach queue: pending email drafts with compliance checks.

Unlike the old /messages/approve, this router returns structured payloads the
dashboard can render (lead name, subject, body, compliance pass/reasons), and
supports edit, skip, regenerate and bulk approve. All sends stay DRY-RUN by
default: 'approve' marks a draft approved for the queue; nothing is ever sent
from here."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.core.audit import record
from app.core.compliance import ComplianceService
from app.core.suppression import SuppressionService
from app.db import get_session
from app.models.campaign import Campaign
from app.models.message import Message
from app.jobs.send import prepare_email_message
from app.llm.service import LLMService
from app.models.lead import Lead

router = APIRouter(prefix='/queue', tags=['outreach-queue'])


class DraftEdit(BaseModel):
    subject: str | None = None
    body: str | None = None


def _campaign_for(db: Session, lead: Lead) -> Campaign | None:
    return db.get(Campaign, lead.campaign_id) if lead.campaign_id else None


def _serialize_draft(db: Session, m: Message) -> dict:
    lead = db.get(Lead, m.lead_id)
    compliance = ComplianceService(suppression=SuppressionService(db),
                                   force_dry_run=settings.force_dry_run)
    campaign = _campaign_for(db, lead) if lead else None
    check = compliance.check(channel='email', campaign=campaign, db=db,
                             email=(lead.contacts[0].value if lead and lead.contacts and lead.contacts[0].kind == 'email' else None) if lead else None)
    return {
        'id': m.id,
        'lead_id': m.lead_id,
        'lead_name': lead.name if lead else '?',
        'lead_category': lead.category if lead else None,
        'subject': m.subject,
        'body': m.body,
        'status': m.status,
        'sequence_step': m.sequence_step,
        'campaign_id': lead.campaign_id if lead else None,
        'compliance': {'ok': check.ok, 'reasons': check.reasons},
        'is_demo': bool(lead and lead.source_place_id.startswith("seed-")),
        'created_at': str(m.created_at) if getattr(m, 'created_at', None) else None,
    }


@router.get('')
def list_queue(status: str | None = None, limit: int = 200, db: Session = Depends(get_session)):
    """List drafts awaiting review (status=draft by default)."""
    q = db.query(Message).filter(Message.channel == 'email')
    if status:
        q = q.filter(Message.status == status)
    else:
        q = q.filter(Message.status.in_(['draft', 'approved']))
    q = q.order_by(Message.created_at.asc()).limit(limit)
    return [_serialize_draft(db, m) for m in q.all()]


def _get_draft(db: Session, message_id: str, expected: set[str] | None = None) -> Message:
    m = db.get(Message, message_id)
    if not m:
        raise HTTPException(404, 'draft not found')
    if expected and m.status not in expected:
        raise HTTPException(409, f'draft is in status {m.status}')
    return m


@router.post('/{message_id}/approve')
def approve_draft(message_id: str, db: Session = Depends(get_session)):
    m = _get_draft(db, message_id, {'draft'})
    m.status = 'approved'
    db.commit()
    record(db, action='approve_draft', lead_id=m.lead_id, detail={'message_id': m.id})
    return _serialize_draft(db, m)


@router.post('/{message_id}/skip')
def skip_draft(message_id: str, db: Session = Depends(get_session)):
    m = _get_draft(db, message_id, {'draft'})
    m.status = 'skipped'
    db.commit()
    record(db, action='skip_draft', lead_id=m.lead_id, detail={'message_id': m.id})
    return _serialize_draft(db, m)


@router.patch('/{message_id}')
def edit_draft(message_id: str, payload: DraftEdit, db: Session = Depends(get_session)):
    m = _get_draft(db, message_id, {'draft'})
    if payload.subject is not None:
        m.subject = payload.subject
    if payload.body is not None:
        m.body = payload.body
    db.commit()
    record(db, action='edit_draft', lead_id=m.lead_id, detail={'message_id': m.id})
    return _serialize_draft(db, m)


@router.post('/{message_id}/regenerate')
def regenerate_draft(message_id: str, db: Session = Depends(get_session)):
    m = _get_draft(db, message_id, {'draft', 'skipped'})
    lead = db.get(Lead, m.lead_id)
    if not lead or not lead.profile:
        raise HTTPException(409, 'lead has no profile to draft from')
    campaign = _campaign_for(db, lead)
    site = lead.demo_sites[-1] if lead.demo_sites else None
    demo_url = site.preview_url if site else 'https://example.com/demo'
    new = prepare_email_message(db, lead, campaign, demo_url=demo_url, llm=LLMService())
    # retire old draft, keep the new one as the pending draft
    m.status = 'superseded'
    db.commit()
    record(db, action='regenerate_draft', lead_id=lead.id, detail={'old': m.id, 'new': new.id})
    return _serialize_draft(db, new)


class BulkApprove(BaseModel):
    ids: list[str]


@router.post('/bulk-approve')
def bulk_approve(payload: BulkApprove, db: Session = Depends(get_session)):
    updated = 0
    for mid in payload.ids:
        m = db.get(Message, mid)
        if m and m.status == 'draft':
            m.status = 'approved'
            updated += 1
    db.commit()
    record(db, action='bulk_approve', detail={'count': updated})
    return {'approved': updated}