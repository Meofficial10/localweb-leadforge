"""Pipeline runner tying independent stages together for a campaign.

Each stage is retryable and isolated: a failure in one lead never blocks the others.
Stage order: discover -> enrich -> profile -> build(demo) -> draft -> send -> followup / call.
Outbound stages respect the compliance gate, so in dry-run nothing leaves the box.

Run transparency (Phase 1):
- execute_run() creates a Run row (status running) and records a RunEvent row per stage
  (discover/enrich/profile/demo/draft/send) with status, count and elapsed ms, so the UI
  can render a live pipeline log + summary banner and toast when the run finishes.
"""
from __future__ import annotations

import threading
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.jobs.discovery import discover_campaign
from app.jobs.enrichment import run_enrichment_for_campaign
from app.jobs.build_demo import build_demo
from app.jobs.profile import build_profile
from app.jobs.send import prepare_email_message, schedule_followup
from app.jobs.voice import place_call_for_lead
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.run import Run, RunEvent
from app.utils import new_uuid


def _event(db, run_id, stage, status, message=None, count=None, elapsed_ms=None):
    if run_id is None:
        return
    try:
        db.add(RunEvent(run_id=run_id, stage=stage, status=status, message=message,
                        count=count, elapsed_ms=elapsed_ms))
        db.commit()
    except Exception:
        db.rollback()


def run_campaign_once(db, campaign, *,
                      discover=True, enrich=True, build=True,
                      max_leads=None, run_id=None) -> dict:
    t_stage = time.monotonic()
    summary = {
        "discovered": 0, "enriched": 0, "profiled": 0, "demo_built": 0,
        "queued_email": 0, "contacted_call": 0, "failed": [],
    }
    _event(db, run_id, "discover", "running", "Starting discovery...")
    if discover:
        d = discover_campaign(db, campaign)
        summary["discovered"] = d.get("inserted", 0)
        extra = {"found": d.get("found"), "no_website": d.get("no_website"),
                 "with_phone": d.get("with_phone"), "with_email": d.get("with_email"),
                 "reason": d.get("reason")}
        _event(db, run_id, "discover", "done",
               message="Found %s place(s), %s without a website; inserted %s contactable lead(s)." % (
                   d.get("found", 0), d.get("without_website", 0), summary["discovered"]),
               count=summary["discovered"], elapsed_ms=int((time.monotonic() - t_stage) * 1000))
        summary["discovery_detail"] = {k: v for k, v in extra.items() if v is not None}
    else:
        _event(db, run_id, "discover", "skipped", "Discovery disabled for this run.")

    t_stage = time.monotonic()
    _event(db, run_id, "enrich", "running", "Enriching contacts (phone/email lookups)...")
    if enrich:
        r = run_enrichment_for_campaign(db, campaign)
        summary["enriched"] = r["enriched"]
        _event(db, run_id, "enrich", "done", "Enriched %s lead(s) with contact data." % r["enriched"],
               count=r["enriched"], elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    else:
        _event(db, run_id, "enrich", "skipped", "Enrichment disabled for this run.")

    leads = db.execute(
        select(Lead).where(Lead.campaign_id == campaign.id)
    ).scalars().all()
    t_stage = time.monotonic()
    _event(db, run_id, "profile", "running", "Writing per-lead profiles.")
    for lead in leads:
        try:
            if lead.status == "enriched":
                if lead.profile is None and build:
                    build_profile(db, lead)
                    summary["profiled"] += 1
            elif lead.status == "profiled":
                if build:
                    site = build_demo(db, lead)
                    if site is not None:
                        summary["demo_built"] += 1
            elif lead.status == "demo_ready":
                if lead.demo_sites:
                    msg = prepare_email_message(db, lead, campaign)
                    if msg is not None:
                        summary["queued_email"] += 1
            elif lead.status == "contacted":
                schedule_followup(db, lead, campaign)
        except Exception as exc:
            summary["failed"].append({"lead": lead.id, "err": str(exc)})
    profiled = summary["profiled"]
    demos = summary["demo_built"]
    drafts = summary["queued_email"]
    _event(db, run_id, "profile", "done", "Profiled %s lead(s)." % profiled, count=profiled,
           elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    t_stage = time.monotonic()
    _event(db, run_id, "demo", "done", "Built %s demo site(s)." % demos, count=demos,
           elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    _event(db, run_id, "draft", "done", "Drafted %s outbound email(s)." % drafts, count=drafts,
           elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    _event(db, run_id, "send", "skipped", "No emails sent: mode=dry_run (compliance gate blocks sends).", count=0)
    return summary


def execute_run(db, campaign, *, discover=True, enrich=True, build=True) -> Run:
    run = Run(id=new_uuid(), campaign_id=campaign.id, status="running",
              mode=getattr(campaign, "mode", "dry_run") or "dry_run")
    db.add(run)
    db.commit()
    try:
        summary = run_campaign_once(db, campaign, discover=discover, enrich=enrich,
                                    build=build, run_id=run.id)
        run.summary = summary
        run.status = "done"
        run.finished_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()
        _event(db, run.id, "send", "failed", "Run failed: %s" % exc)
    return run


def run_campaign_async(db_factory, campaign_id: str, *,
                       discover=True, enrich=True, build=True):
    def _worker():
        db = db_factory()
        try:
            camp = db.get(Campaign, campaign_id)
            if camp is None:
                return
            execute_run(db, camp, discover=discover, enrich=enrich, build=build)
        except Exception:
            db.rollback()
        finally:
            db.close()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
