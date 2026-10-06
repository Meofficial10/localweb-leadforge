"""Suppression list endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.suppression import SuppressionService
from app.db import get_session

router = APIRouter(prefix="/suppression", tags=["compliance"])


class SuppressRequest(BaseModel):
    kind: str
    value: str
    reason: str | None = None


@router.get("")
def list_suppressions(db: Session = Depends(get_session)):
    return SuppressionService(db).list_all()


@router.post("")
def add_suppression(payload: SuppressRequest, db: Session = Depends(get_session)):
    svc = SuppressionService(db)
    svc.add(payload.kind, payload.value, payload.reason)
    return {"added": True}
