"""Audit log service. Every outbound message and call is recorded here."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    action: str,
    lead_id: str | None = None,
    actor: str = "system",
    detail: dict | None = None,
) -> AuditLog:
    entry = AuditLog(lead_id=lead_id, actor=actor, action=action, detail=detail or {})
    db.add(entry)
    db.commit()  # audit is written independently so it survives later failures
    return entry
