"System endpoints: kill switch, status (effective mode), metrics, audit log."
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.core.effective_mode import effective_channel_mode, effective_campaign_modes
from app.core.metrics import overview_metrics
from app.core.settings_service import get_setting, is_system_paused, set_setting
from app.db import get_session
from app.models.audit_log import AuditLog
from app.models.campaign import Campaign

router = APIRouter(prefix="/system", tags=["system"])


class PauseRequest(BaseModel):
    paused: bool


@router.post("/pause")
def set_pause(payload: PauseRequest, db: Session = Depends(get_session)):
    set_setting(db, "system.paused", payload.paused)
    return {"paused": payload.paused}


@router.get("/status")
def status(db: Session = Depends(get_session)):
    """Global status with EFFECTIVE modes. Never reports live when the system
    forces dry-run."""
    return {
        "paused": is_system_paused(db),
        "force_dry_run": settings.force_dry_run,
        "channels": {
            "email": {
                "paused": get_setting(db, "channel.email.paused", False),
                "effective_mode": effective_channel_mode(db, "email"),
            },
            "voice": {
                "paused": get_setting(db, "channel.voice.paused", False),
                "effective_mode": effective_channel_mode(db, "voice"),
            },
        },
        "bounce_rate": float(get_setting(db, "stats.bounce_rate", 0.0) or 0.0),
        "complaint_rate": float(get_setting(db, "stats.complaint_rate", 0.0) or 0.0),
        "bounce_threshold": settings.bounce_rate_pause_threshold,
        "complaint_threshold": settings.spam_complaint_pause_threshold,
    }


@router.get("/campaign-modes")
def campaign_modes(campaign_id: str | None = None, db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id) if campaign_id else None
    modes = effective_campaign_modes(db, camp)
    return {
        "campaign_id": camp.id if camp else None,
        "campaign_mode": (camp.mode if camp else "dry_run"),
        "effective": modes,
    }


@router.get("/metrics")
def metrics(db: Session = Depends(get_session)):
    return overview_metrics(db)


@router.get("/audit")
def audit_log(
    limit: int = 100,
    action: str | None = None,
    lead_id: str | None = None,
    page: int | None = None,
    page_size: int = 25,
    db: Session = Depends(get_session),
):
    """Audit log with filters and server-side pagination (M5).

    Backwards-compatible: without `page` returns a flat list capped by
    `limit` (legacy); with `page` returns a paginated envelope.
    """
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if lead_id:
        q = q.filter(AuditLog.lead_id == lead_id)
    if page is None:
        rows = q.order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
        out = []
        for r in rows:
            out.append({
                "id": r.id, "action": r.action, "lead_id": r.lead_id,
                "detail": r.detail, "created_at": str(r.created_at) if r.created_at else None,
            })
        return out
    page = max(int(page), 1)
    page_size = min(max(int(page_size), 1), 100)
    total = q.count()
    rows = q.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id, "action": r.action, "lead_id": r.lead_id,
            "detail": r.detail, "created_at": str(r.created_at) if r.created_at else None,
        })
    return {"items": out, "total": total, "page": page, "page_size": page_size}



# ---- M5: combined overview endpoint with a short TTL cache ----
_overview_cache: dict = {"at": 0.0, "data": None}
_CACHE_TTL_S = 5.0


def _audit_rows(db: Session, limit: int, action: str | None, lead_id: str | None):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if lead_id:
        q = q.filter(AuditLog.lead_id == lead_id)
    rows = q.order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id, "action": r.action, "lead_id": r.lead_id,
            "detail": r.detail, "created_at": str(r.created_at) if r.created_at else None,
        })
    return out


@router.get("/overview")
def overview(db: Session = Depends(get_session)):
    """One endpoint for the Overview page: metrics + status + caps + recent
    audit, cached in-process for a few seconds so the page makes a single
    round-trip instead of four (M5). The cache is keyed for a single-user
    local console, so a tiny TTL keeps values fresh without DB churn."""
    import time as _time
    now = _time.time()
    if _overview_cache["data"] is not None and (now - _overview_cache["at"]) < _CACHE_TTL_S:
        return _overview_cache["data"]
    metrics = overview_metrics(db)
    stat = status(db)
    try:
        from app.api.routers.settings_routes import _all as _all_settings
        caps = _all_settings(db)
    except Exception:  # pragma: no cover - fallback below
        caps = {}
    data = {"metrics": metrics, "status": stat, "caps": caps, "audit": _audit_rows(db, 8, None, None)}
    _overview_cache["at"] = now
    _overview_cache["data"] = data
    return data