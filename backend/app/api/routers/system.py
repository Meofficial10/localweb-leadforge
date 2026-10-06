"""System endpoints: kill switch, compliance stats, audit log."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.settings_service import get_setting, is_system_paused, set_setting
from app.db import get_session
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/system", tags=["system"])


class PauseRequest(BaseModel):
    paused: bool


@router.post("/pause")
def set_pause(payload: PauseRequest, db: Session = Depends(get_session)):
    set_setting(db, "system.paused", payload.paused)
    return {"paused": payload.paused}


@router.get("/status")
def status(db: Session = Depends(get_session)):
    return {
        "paused": is_system_paused(db),
        "email_paused": get_setting(db, "channel.email.paused", False),
        "voice_paused": get_setting(db, "channel.voice.paused", False),
        "bounce_rate": get_setting(db, "stats.bounce_rate", 0.0),
        "complaint_rate": get_setting(db, "stats.complaint_rate", 0.0),
    }


@router.get("/audit")
def audit_log(limit: int = 100, db: Session = Depends(get_session)):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500)).all()
