"""Scheduler: cron-like jobs per campaign using APScheduler in-process (v1).

The scheduler polls due campaigns and advances the pipeline. For dry-run safety it
only runs stages that never send: discovery/enrichment/profile/build are safe; the
send/call steps only execute when the compliance gate approves (which blocks in
dry-run because mode != live).
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import get_sync_session
from app.jobs.pipeline import run_campaign_once
from app.models.campaign import Campaign

logger = logging.getLogger(__name__)


def _tick() -> None:
    """One scheduler pass: run discovery on non-paused campaigns."""
    db = get_sync_session()
    try:
        campaigns = db.query(Campaign).filter(Campaign.is_paused.is_(False)).all()
        for camp in campaigns:
            try:
                run_campaign_once(db, camp, discover=True, enrich=True, build=True)
            except Exception as exc:  # noqa: BLE001
                logger.exception("campaign tick failed: %s", exc)
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    sched = BackgroundScheduler(timezone="Asia/Singapore")
    sched.add_job(_tick, CronTrigger(hour="8,12,16", minute="5"), id="pipeline-tick", replace_existing=True)
    sched.start()
    logger.info("scheduler started (cron 08:05,12:05,16:05 SGT)")
    return sched


def stop_scheduler(sched: BackgroundScheduler | None) -> None:
    if sched is not None:
        sched.shutdown(wait=False)
