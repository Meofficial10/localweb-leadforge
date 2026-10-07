"Suppression list endpoints: add, list, remove, search, CSV import/export."
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.suppression import SuppressionService
from app.db import get_session
from app.models.suppression import Suppression

router = APIRouter(prefix="/suppression", tags=["compliance"])


class SuppressRequest(BaseModel):
    kind: str
    value: str
    reason: str | None = None


def _row(r):
    return {
        "id": r.id,
        "kind": r.kind,
        "value": r.value,
        "reason": r.reason,
        "created_at": str(r.created_at) if r.created_at else None,
    }


@router.get("")
def list_suppressions(search: str | None = None, db: Session = Depends(get_session)):
    q = db.query(Suppression)
    if search:
        like = "%" + search + "%"
        q = q.filter(Suppression.value.ilike(like) | Suppression.reason.ilike(like))
    rows = q.order_by(Suppression.created_at.desc()).limit(1000).all()
    return [_row(r) for r in rows]


@router.post("")
def add_suppression(payload: SuppressRequest, db: Session = Depends(get_session)):
    svc = SuppressionService(db)
    svc.add(payload.kind, payload.value, payload.reason)
    record(db, action="suppression_add", detail={"kind": payload.kind, "value": payload.value})
    return {"added": True}


@router.delete("/{suppression_id}")
def remove_suppression(
    suppression_id: str,
    reason: str | None = None,
    db: Session = Depends(get_session),
):
    row = db.get(Suppression, suppression_id)
    if not row:
        raise HTTPException(404, "suppression entry not found")
    db.delete(row)
    db.commit()
    record(db, action="suppression_remove", detail={"value": row.value, "reason": reason})
    return {"removed": True}


@router.post("/import-csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_session)):
    raw = await file.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    svc = SuppressionService(db)
    added = 0
    skipped = 0
    for row in reader:
        kind = (row.get("kind") or "").strip().lower()
        value = (row.get("value") or "").strip()
        reason = (row.get("reason") or "").strip() or "csv import"
        if kind not in ("email", "phone", "domain") or not value:
            skipped += 1
            continue
        try:
            svc.add(kind, value, reason)
            added += 1
        except Exception:
            skipped += 1
    db.commit()
    record(db, action="suppression_import", detail={"added": added, "skipped": skipped})
    return {"added": added, "skipped": skipped}


@router.get("/export.csv")
def export_csv(db: Session = Depends(get_session)):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["kind", "value", "reason", "created_at"])
    for r in db.query(Suppression).order_by(Suppression.created_at.desc()):
        writer.writerow([r.kind, r.value, r.reason or "", str(r.created_at) if r.created_at else ""])
    data = buf.getvalue()
    return Response(content=data, media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=suppression-list.csv"})