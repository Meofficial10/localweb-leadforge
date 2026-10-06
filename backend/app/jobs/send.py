"""SEND + FOLLOW-UP orchestration for email leads.

Queues approved drafts for sending (respecting compliance gate), records the
message, and on 'contacted' schedules a single follow-up after 3-4 days unless
the lead replied/opted out.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.audit import record
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
    draft: DraftResult = draft_email(lead, profile, demo_url)
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
    """Compliance-gated send. Returns {ok, status, error}."""
    if msg.status not in ("approved", "queued"):
        return {"ok": False, "status": msg.status, "error": f"not sendable (status={msg.status})"}

    lead = db.query(Lead).get(msg.lead_id)
    email = None
    if lead:
        emails = [c.value for c in lead.contacts if c.kind == "email"]
        email = emails[0] if emails else None
    if not email:
        return {"ok": False, "status": "failed", "error": "no email contact"}

    suppression = suppression or SuppressionService(db)
    compliance = compliance or ComplianceService(suppression=suppression)
    check = compliance.check(
        channel="email", email=email, campaign=campaign, db=db,
    )
    if not check.ok:
        return {"ok": False, "status": "blocked", "error": compliance.block_reason_string(check)}

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
    """Create one follow-up message (step 2) if no reply/opt-out occurred."""
    if lead.status != "contacted":
        return None
    # only one follow-up
    if any(m.sequence_step == 2 for m in lead.messages):
        return None
    demo_url = lead.demo_sites[-1].preview_url if lead.demo_sites else None
    follow = Message(
        id=new_uuid(),
        lead_id=lead.id,
        channel="email",
        direction="outbound",
        sequence_step=2,
        subject=f"Following up on {lead.name or 'your business'}",
        body=f"Just following up on my note about {lead.name}. "
             f"The demo is still here: {demo_url}. "
             "Happy to stop if you're not interested — just reply 'stop'.",
        status="draft",
    )
    db.add(follow)
    lead.status = transition(lead.status, "followup_sent")
    db.commit()
    return follow
