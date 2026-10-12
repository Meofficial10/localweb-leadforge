"""SEND + FOLLOW-UP orchestration for email leads.

Queues approved drafts for sending (respecting compliance gate), records the
message, and on 'contacted' schedules a single follow-up after 3-4 days unless
the lead replied/opted out.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.core.audit import record
from app.core.facts import collect_verified_facts
from app.core.compliance import ComplianceService
from app.core.state_machine import transition
from app.core.suppression import SuppressionService
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.message import Message
from app.outreach.email.draft import DraftResult, draft_email
from app.outreach.email.sender import EmailSender, FileSender, SendResult
from app.outreach.email.unsubscribe import unsubscribe_url
from app.utils import new_uuid


def prepare_email_message(db: Session, lead: Lead, campaign: Campaign | None,
                          demo_url: str | None = None,
                          llm=None) -> Message:
    """Create the first-touch outbound email message (draft) for a demo-ready lead."""
    profile = lead.profile
    site = lead.demo_sites[-1] if lead.demo_sites else None
    demo_url = demo_url or (site.preview_url if site else "https://example.com/demo")
    facts_rows = collect_verified_facts(db, lead)
    facts_dicts = [{"id": r.id, "field": r.field, "value": r.value,
                      "source": r.source, "is_null_fact": r.is_null_fact} for r in facts_rows]
    draft: DraftResult = draft_email(lead, profile, demo_url, facts=facts_dicts)
    msg = Message(
        id=new_uuid(),
        lead_id=lead.id,
        channel="email",
        direction="outbound",
        sequence_step=1,
        subject=draft.subject,
        body=draft.body,
        status="draft",
    )
    db.add(msg)
    lead.status = transition(lead.status, "queued_email")
    db.commit()
    return msg


def send_message(
    db: Session,
    msg: Message,
    campaign: Campaign | None = None,
    sender: EmailSender | None = None,
    compliance: ComplianceService | None = None,
    suppression: SuppressionService | None = None,
) -> dict[str, Any]:
    """Compliance-gated send. Returns {ok, status, error}.

    Dry-run is enforced at the sender level TOO: if global force_dry_run is set
    (or the campaign is in dry-run mode), the only allowed sink is the local file
    outbox (FileSender) even when a caller passes a real provider adapter - so a
    stray SMTP/Brevo instance can never fire during a dry-run queue.
    """
    if msg.status not in ("approved", "queued"):
        return {"ok": False, "status": msg.status, "error": "not sendable (status=%s)" % msg.status}

    lead = db.query(Lead).get(msg.lead_id)
    email = None
    if lead:
        emails = [c.value for c in lead.contacts if c.kind == "email"]
        email = emails[0] if emails else None
    if not email:
        return {"ok": False, "status": "failed", "error": "no email contact"}

    suppression = suppression or SuppressionService(db)
    dry_run_active = settings.force_dry_run or bool(campaign and getattr(campaign, "mode", "dry_run") == "dry_run")
    # Hardening (Workstream F): compliance is always checked and fails closed, but
    # when dry-run is active the "in dry-run mode" reason is NOT fatal - it is the
    # whole point: the send goes to the local file outbox (FileSender), which is
    # the safe sink that cannot reach any recipient. All other gates (suppression,
    # rate caps, DNC) still block. A real provider adapter is never used in dry-run:
    # it is replaced by FileSender regardless of what the caller passes.
    if compliance is None:
        compliance = ComplianceService(suppression=suppression,
                                       force_dry_run=settings.force_dry_run)
    check = compliance.check(
        channel="email", email=email, campaign=campaign, db=db,
    )
    non_dry_run_reasons = [r for r in check.reasons
                           if not r.startswith("channel email in dry-run")] if not check.ok else []
    if non_dry_run_reasons:
        return {"ok": False, "status": "blocked", "error": "; ".join(non_dry_run_reasons)}

    if dry_run_active:
        sender = FileSender()
    else:
        sender = sender or FileSender()

    result: SendResult = sender.send(
        to=email,
        subject=msg.subject or "",
        body=msg.body or "",
        from_name="LeadForge Demo",
        from_addr="demo@leads.example.com",
        unsubscribe_url=unsubscribe_url(lead.id, msg.id),
    )
    if not result.success:
        return {"ok": False, "status": "failed", "error": result.error}

    msg.status = "sent"
    msg.provider_message_id = result.provider_message_id
    msg.sent_at = __import__("datetime").datetime.now()
    if lead:
        lead.status = transition(lead.status, "contacted")
    db.commit()
    record(db, action="send_email", lead_id=lead.id if lead else None,
           detail={"message_id": msg.id, "provider_id": result.provider_message_id})
    return {"ok": True, "status": "sent"}


def schedule_followup(db: Session, lead: Lead, campaign: Campaign | None = None,
                      days_delay: int = 4) -> Message | None:
    """Create one scheduled follow-up message (step 2) when the first touch is sent.

    Follow-ups are never sent immediately: schedule_followup sets scheduled_at to
    now + days_delay (default 4 days) and the message stays a draft. It returns
    None when the lead is not contacted, already has a step-2 draft, or has
    replied/opted out (an inbound reply or opt-out cancels the pending follow-up).
    """
    if lead.status != "contacted":
        return None
    # only one follow-up, and never stack it on top of a reply/opt-out
    if any(m.sequence_step == 2 for m in lead.messages):
        return None
    if any(m.direction == "inbound" or m.status in ("replied", "opted_out") for m in lead.messages):
        return None
    demo_url = lead.demo_sites[-1].preview_url if lead.demo_sites else None
    follow = Message(
        id=new_uuid(),
        lead_id=lead.id,
        channel="email",
        direction="outbound",
        sequence_step=2,
        subject=f"Following up on {lead.name or 'your business'}",
        body=(f"Just following up on my note about {lead.name}. "
              f"The demo is still here: {demo_url}. "
              "Happy to stop if you're not interested - just reply 'stop'."),
        status="draft",
        scheduled_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                 + __import__("datetime").timedelta(days=days_delay),
    )
    db.add(follow)
    lead.status = transition(lead.status, "followup_sent")
    db.commit()
    return follow
