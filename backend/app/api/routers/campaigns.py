"""Campaign CRUD + run trigger + duplicate."""
from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.audit import record
from app.db import get_session
from app.models.campaign import Campaign
from app.models.job import Job
from app.jobs.pipeline import run_campaign_once

router = APIRouter(prefix='/campaigns', tags=['campaigns'])


class CampaignCreate(BaseModel):
    name: str
    country: str = 'Singapore'
    city: str
    area_radius_km: Optional[float] = None
    categories: list[str] = Field(default_factory=list)
    lead_source: str = 'both'  # google | osm | both (legacy)
    lead_sources: Optional[list[str]] = None  # ["google","osm","apify"] multi-select
    daily_email_cap: int | None = None
    daily_call_cap: int | None = None
    max_leads_per_run: int | None = None
    send_window: dict | None = None
    timezone: str = 'Asia/Singapore'
    warm_up_schedule: dict | None = None
    followup_delay_days: int = 4
    approval_mode: str = 'manual'  # auto | manual
    cron_schedule: dict | None = None
    mode: str = 'dry_run'


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    area_radius_km: Optional[float] = None
    categories: Optional[list[str]] = None
    lead_source: Optional[str] = None
    lead_sources: Optional[list[str]] = None
    daily_email_cap: Optional[int] = None
    daily_call_cap: Optional[int] = None
    max_leads_per_run: Optional[int] = None
    send_window: Optional[dict] = None
    timezone: Optional[str] = None
    warm_up_schedule: Optional[dict] = None
    followup_delay_days: Optional[int] = None
    approval_mode: Optional[str] = None
    cron_schedule: Optional[dict] = None
    mode: Optional[str] = None
    is_paused: Optional[bool] = None


def _serialize(camp: Campaign) -> dict:
    return {
        'id': camp.id,
        'name': camp.name,
        'country': camp.country,
        'city': camp.city,
        'area_radius_km': camp.area_radius_km,
        'categories': camp.categories or [],
        'lead_source': camp.lead_source,
        'lead_sources': camp.lead_sources or [],
        'daily_email_cap': camp.daily_email_cap,
        'daily_call_cap': camp.daily_call_cap,
        'max_leads_per_run': camp.max_leads_per_run,
        'send_window': camp.send_window,
        'timezone': camp.timezone,
        'warm_up_schedule': camp.warm_up_schedule,
        'followup_delay_days': camp.followup_delay_days,
        'approval_mode': camp.approval_mode,
        'cron_schedule': camp.cron_schedule,
        'mode': camp.mode,
        'is_paused': camp.is_paused,
        'created_at': str(camp.created_at) if camp.created_at else None,
        'updated_at': str(camp.updated_at) if getattr(camp, 'updated_at', None) else None,
    }


@router.get('')
def list_campaigns(db: Session = Depends(get_session)):
    return [_serialize(c) for c in db.query(Campaign).order_by(Campaign.created_at.desc()).all()]


@router.post('')
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_session)):
    # NEVER let a caller force live: global dry-run wins
    mode = 'dry_run' if settings.force_dry_run else payload.mode
    cap_email = int(payload.daily_email_cap or settings.default_daily_email_cap)
    warm = payload.warm_up_schedule
    if warm is None and settings.warmup_start_daily_email:
        warm = {'mode': 'ramp', 'start': settings.warmup_start_daily_email, 'days': 21, 'target': cap_email}
    camp = Campaign(
        id=str(uuid.uuid4()),
        name=payload.name,
        country=payload.country,
        city=payload.city,
        area_radius_km=payload.area_radius_km,
        categories=payload.categories or [],
        lead_source=payload.lead_source,
        lead_sources=payload.lead_sources or None,
        daily_email_cap=cap_email,
        daily_call_cap=int(payload.daily_call_cap or settings.default_daily_call_cap),
        max_leads_per_run=payload.max_leads_per_run,
        send_window=payload.send_window,
        timezone=payload.timezone,
        warm_up_schedule=warm,
        followup_delay_days=payload.followup_delay_days,
        approval_mode=payload.approval_mode,
        cron_schedule=payload.cron_schedule,
        mode=mode,
        is_paused=False,
    )
    db.add(camp)
    db.commit()
    record(db, action='campaign_created', detail={'campaign_id': camp.id, 'name': camp.name})
    return _serialize(camp)


@router.get('/{campaign_id}')
def get_campaign(campaign_id: str, db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, 'campaign not found')
    return _serialize(camp)


@router.patch('/{campaign_id}')
def update_campaign(campaign_id: str, payload: CampaignUpdate, db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, 'campaign not found')
    data = payload.model_dump(exclude_unset=True)
    if 'mode' in data and data['mode'] != 'dry_run' and settings.force_dry_run:
        data['mode'] = 'dry_run'
    for k, v in data.items():
        setattr(camp, k, v)
    db.commit()
    record(db, action='campaign_updated', detail={'campaign_id': camp.id})
    return _serialize(camp)


@router.delete('/{campaign_id}')
def delete_campaign(campaign_id: str, db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, 'campaign not found')
    db.delete(camp)
    db.commit()
    record(db, action='campaign_deleted', detail={'campaign_id': campaign_id})
    return {'deleted': True}


@router.post('/{campaign_id}/run')
def trigger_run(campaign_id: str, db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, 'campaign not found')
    return run_campaign_once(db, camp)


@router.patch('/{campaign_id}/pause')
def set_pause(campaign_id: str, paused: bool = Query(True), db: Session = Depends(get_session)):
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, 'campaign not found')
    camp.is_paused = bool(paused)
    db.commit()
    record(db, action='campaign_paused' if paused else 'campaign_resumed', detail={'campaign_id': camp.id})
    return _serialize(camp)


@router.post('/{campaign_id}/duplicate')
def duplicate_campaign(campaign_id: str, db: Session = Depends(get_session)):
    src = db.get(Campaign, campaign_id)
    if not src:
        raise HTTPException(404, 'campaign not found')
    copy = Campaign(
        id=str(uuid.uuid4()),
        name=src.name + ' (copy)',
        country=src.country,
        city=src.city,
        area_radius_km=src.area_radius_km,
        categories=list(src.categories or []),
        lead_source=src.lead_source,
        lead_sources=list(src.lead_sources or []) or None,

        daily_email_cap=src.daily_email_cap,
        daily_call_cap=src.daily_call_cap,
        max_leads_per_run=src.max_leads_per_run,
        send_window=({**src.send_window} if src.send_window else None),
        timezone=src.timezone,
        warm_up_schedule=({**src.warm_up_schedule} if src.warm_up_schedule else None),
        followup_delay_days=src.followup_delay_days,
        approval_mode=src.approval_mode,
        cron_schedule=({**src.cron_schedule} if src.cron_schedule else None),
        mode='dry_run',
        is_paused=True,  # copies start paused for review
    )
    db.add(copy)
    db.commit()
    record(db, action='campaign_duplicated', detail={'src': src.id, 'copy': copy.id})
    return _serialize(copy)

class RunView(BaseModel):
    pass

@router.get('/{campaign_id}/runs')
def list_campaign_runs(campaign_id: str, db: Session = Depends(get_session)):
    """Run history for the campaign run view (apify actor runs)."""
    camp = db.get(Campaign, campaign_id)
    if not camp:
        raise HTTPException(404, 'campaign not found')
    from app.models.apify_run import ApifyRun
    apify_runs = db.query(ApifyRun).filter(ApifyRun.campaign_id == campaign_id).order_by(ApifyRun.created_at.desc()).limit(10).all()
    return {"apify_runs": [{
        "id": r.id, "apify_run_id": r.apify_run_id, "actor_id": r.actor_id,
        "search": r.search, "status": r.status, "items_fetched": r.items_fetched,
        "leads_imported": r.leads_imported, "estimated_cost_usd": r.estimated_cost_usd,
        "error": r.error,
        "created_at": str(r.created_at) if r.created_at else None,
        "finished_at": str(r.finished_at) if r.finished_at else None,
    } for r in apify_runs], "jobs": []}
