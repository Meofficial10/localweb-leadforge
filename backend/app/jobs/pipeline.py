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
from app.core.state_machine import transition
from app.enrichment.service import EnrichmentService
from app.jobs.send import prepare_email_message, schedule_followup
from app.jobs.voice import CALL_SCRIPT, place_call_for_lead
from app.models.campaign import Campaign
from app.core.dnc import DNCRegistry
from app.models.lead import Lead
from app.models.message import Message
from app.models.run import Run, RunEvent
from app.utils import new_uuid


def _reason_count(summary: dict, reason: str | None) -> None:
    """Track per-reason tally for no-contact leads (run summary shows
    counts per stage AND per reason)."""
    key = (reason or "unknown").strip() or "unknown"
    summary.setdefault("reasons", {})
    summary["reasons"][key] = summary["reasons"].get(key, 0) + 1


def _event(db, run_id, stage, status, message=None, count=None, elapsed_ms=None):
    if run_id is None:
        return
    try:
        db.add(RunEvent(run_id=run_id, stage=stage, status=status, message=message,
                        count=count, elapsed_ms=elapsed_ms))
        db.commit()
    except Exception:
        db.rollback()




def _draft_phone_outreach(db, lead: Lead, campaign: Campaign | None) -> dict:
    """Draft outbound WhatsApp/text short draft + call-script draft for phone leads.
    Both carry AI disclosure + DNC status. They are drafts only: sending remains
    compliance-gated (dry-run)."""
    phones = [c.value for c in lead.contacts if c.kind == "phone"]
    if not phones:
        return {"chat": False, "call_script": False, "dnc": None}
    phone = phones[0]
    dnc = _dnc_status(db, phone)
    business = lead.name or "your business"
    campaign_label = (campaign.name if campaign else "our team")
    chat_body = (
        f"Hi {business}, this is an AI assistant writing on behalf of {campaign_label}."
        f" I'd love to share something we built for you: a free demo page."
        f" AI disclosure: this draft was written by an AI assistant for review only."
        f" DNC status: {dnc}. Reply STOP to opt out."
    )
    chat = Message(id=new_uuid(), lead_id=lead.id, channel="whatsapp",
                   direction="outbound", sequence_step=1,
                   subject="WhatsApp/text draft", body=chat_body, status="draft")
    db.add(chat)
    call = Message(id=new_uuid(), lead_id=lead.id, channel="voice",
                   direction="outbound", sequence_step=1,
                   subject="Call script draft",
                   body=CALL_SCRIPT.format(sender=campaign_label, business=business)
                          + "\n\n[DNC] " + dnc,
                   status="draft")
    db.add(call)
    db.commit()
    return {"chat": True, "call_script": True, "dnc": dnc}

def _dnc_status(db, phone: str) -> str:
    """Return human-readable DNC screening status for a phone number.
    Uses the configured registry (fail-closed). Powers the WhatsApp/text draft
    disclosure line; never a real send."""
    from app.core.dnc import DNCRegistry
    from app.utils import normalize_phone
    norm = normalize_phone(phone)
    try:
        reg = DNCRegistry()
        ok = reg.check(norm)
    except Exception:
        return "blocked (DNC check unavailable)"
    if not ok:
        return "on DNC registry - no call/text (must not be sent)"
    return "clear for outreach (DNC checked, dry-run only)"

def run_campaign_once(db, campaign, *,
                      discover=True, enrich=True, build=True,
                      max_leads=None, run_id=None) -> dict:
    t_stage = time.monotonic()
    summary = {
        "discovered": 0, "enriched": 0, "profiled": 0, "demo_built": 0,
        "queued_email": 0, "queued_call": 0, "contacted_call": 0,
        "no_contact": 0, "reasons": {}, "failed": [],
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
        summary["no_contact"] += r.get("no_contact", 0)
        for reason, count in (r.get("reasons") or {}).items():
            summary["reasons"][reason] = summary["reasons"].get(reason, 0) + count
        _event(db, run_id, "enrich", "done", "Enriched %s lead(s) with contact data; %s with no contact." % (
            r["enriched"], r.get("no_contact", 0)),
               count=r["enriched"], elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    else:
        _event(db, run_id, "enrich", "skipped", "Enrichment disabled for this run.")

    leads = db.execute(
        select(Lead).where(Lead.campaign_id == campaign.id)
    ).scalars().all()
    t_stage = time.monotonic()
    _event(db, run_id, "profile", "running", "Writing per-lead profiles.")
    enrichment = EnrichmentService()
    # Per lead: advance through ALL remaining pipeline stages in this run
    # (discover -> enrich -> profile -> demo -> draft), so one run fully
    # prepares every contactable lead instead of advancing a single stage.
    for lead in leads:
        try:
            guard = 0
            while guard < 6:
                guard += 1
                st = lead.status
                if st == "discovered" and enrich:
                    r = enrichment.enrich(db, lead)
                    if r.get("classification") in ("email", "phone", "both"):
                        summary["enriched"] += 1
                    elif r.get("classification") == "none":
                        summary["no_contact"] += 1
                        _reason_count(summary, lead.no_contact_reason)
                elif st == "enriched":
                    if lead.profile is None and build:
                        build_profile(db, lead)
                        summary["profiled"] += 1
                elif st == "profiled":
                    if build:
                        site = build_demo(db, lead)
                        if site is not None:
                            summary["demo_built"] += 1
                elif st == "demo_ready":
                    contacts = {c.kind for c in lead.contacts}
                    if "email" in contacts:
                        msg = prepare_email_message(db, lead, campaign)
                        if msg is not None:
                            summary["queued_email"] += 1
                    elif "phone" in contacts:
                        d = _draft_phone_outreach(db, lead, campaign)
                        if d.get("call_script"):
                            summary["queued_call"] += 1
                        lead.status = transition("demo_ready", "queued_call")
                        db.commit()
                        _event(db, run_id, "draft_voice", "done", 
                              "Phone-only lead drafted: WhatsApp/text + call script (AI disclosure, DNC status).",
                               count=1, elapsed_ms=0)
                    else:
                        # no contact at all -> terminal no_contact with reason
                        lead.status = transition("demo_ready", "rejected")
                        lead.no_contact_reason = "no contact data to draft against"
                        summary["no_contact"] += 1
                        _reason_count(summary, lead.no_contact_reason)
                elif st == "contacted":
                    schedule_followup(db, lead, campaign)
                else:
                    break
        except Exception as exc:
            summary["failed"].append({"lead": lead.id, "err": str(exc)})
    profiled = summary["profiled"]
    demos = summary["demo_built"]
    drafts = summary["queued_email"]
    calls_drafts = summary["queued_call"]
    no_contact = summary["no_contact"]
    _event(db, run_id, "profile", "done", "Profiled %s lead(s)." % profiled, count=profiled,
           elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    t_stage = time.monotonic()
    _event(db, run_id, "demo", "done", "Built %s demo site(s)." % demos, count=demos,
           elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    _event(db, run_id, "draft", "done", "Drafted %s outbound email(s) and %s text/call script(s)." % (drafts, calls_drafts),
           count=drafts + calls_drafts, elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    _event(db, run_id, "no_contact", "done", "%s lead(s) with no contact info." % no_contact, count=no_contact,
           elapsed_ms=int((time.monotonic() - t_stage) * 1000))
    _event(db, run_id, "send", "skipped", "No emails/calls sent: mode=dry_run (compliance gate blocks sends).", count=0)
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
