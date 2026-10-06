"""Campaign CRUD + run trigger."""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_session
from app.models.campaign import Campaign
from app.jobs.pipeline import run_campaign_once

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    country: str = "Singapore"
    city: str
    categories: list[str]
    daily_email_cap: int | None = None
    daily_call_cap: int | None = None
    send_window: dict | None = None
    mode: str = "dry_run"


def _serialize(camp: Campaign) -> dict:
    return {
        "id": camp.id,
        "name": camp.name,
        "country": camp.country,
        "city": camp.city,
        "categories": camp.categories,
        "daily_email_cap": camp.daily_email_cap,
        "daily_call_cap": camp.daily_call_cap,
        "send_window": camp.send_window,
        "mode": camp.mode,
        "is_paused": camp.is_paused,
        "created_at": str(camp.created_at),
    }


@router.get("")
def list_campaigns(db: Session = Depends(get_session)):
    return [_serialize(c) for c in db.query(Campaign).all()]


@router.post("")
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_session)):
    mode = payload.mode if not settings.force_dry_run else "dry_run"
    cap_email = (payload.daily_email_cap or settings.default_daily_email_cap)
    if payload.daily_email_cap is None and settings.warmup_start_daily_email:
        cap_email = min(cap_email, settings.warmup_start_daily_email)
    camp = Campaign(
        id=str(uuid.uuid4()),
        name=payload.name,
        country=payload.country,
        city=payload.city,
        categories=payload.categories,
        daily_email_cap=cap_email,
        daily_call_cap=payload.daily_call_cap or settings.default_daily_call_cap,
        send_window=payload.send_window,
        mode=mode,
        is_paused=False,
    )
    db.add(camp)
    db.commit()
    return _serialize(camp)


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str, db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, "campaign not found")
    return _serialize(camp)


@router.post("/{campaign_id}/run")
def trigger_run(campaign_id: str, db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, "campaign not found")
    return run_campaign_once(db, camp)


@router.patch("/{campaign_id}/pause")
def set_pause(campaign_id: str, paused: bool, db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, "campaign not found")
    camp.is_paused = paused
    db.commit()
    return _serialize(camp)
