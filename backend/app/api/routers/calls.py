"""Calls list with outcome, duration, transcript, DNC + AI disclosure."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_session
from app.models.call import Call
from app.models.lead import Lead

router = APIRouter(prefix='/calls', tags=['calls'])


def _serialize(db: Session, c: Call) -> dict:
    lead = db.get(Lead, c.lead_id) if c.lead_id else None
    return {
        'id': c.id,
        'lead_id': c.lead_id,
        'lead_name': lead.name if lead else '?',
        'provider_call_id': c.provider_call_id,
        'dnc_checked_at': str(c.dnc_checked_at) if c.dnc_checked_at else None,
        'ai_disclosed': c.ai_disclosed,
        'started_at': str(c.started_at) if c.started_at else None,
        'duration_sec': c.duration_sec,
        'outcome': c.outcome,
        'transcript': c.transcript,
        'recording_url': c.recording_url,
        'recording_consent': c.recording_consent,
    }


@router.get('')
def list_calls(limit: int = 200, db: Session = Depends(get_session)):
    return [_serialize(db, c) for c in db.query(Call).order_by(Call.started_at.desc().nullslast()).limit(limit).all()]