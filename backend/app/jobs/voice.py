"""CALL stage for phone-only leads with mandatory AI disclosure.

Flow: compliance gate (DNC + call window + suppression + caps) -> build script ->
place call (via adapter) -> log transcript/outcome/consent -> update state.
Phone numbers that fail the DNC check (or whose check cannot complete) are never called.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.compliance import ComplianceService
from app.core.state_machine import transition
from app.core.suppression import SuppressionService
from app.models.call import Call
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.outreach.voice.provider import CallRequest, MockVoiceProvider, VoiceProvider
from app.utils import new_uuid, normalize_phone

CALL_SCRIPT = (
    "Hi, this is an AI assistant calling on behalf of {sender}. "
    "I put together a demo website for {business} and was hoping to share it with you. "
    "You can end this call at any time, or I can have a human follow up by email instead. "
    "Would you like me to send over a link?"
)


def place_call_for_lead(
    db: Session,
    lead: Lead,
    campaign: Campaign | None = None,
    provider: VoiceProvider | None = None,
    compliance: ComplianceService | None = None,
    suppression: SuppressionService | None = None,
) -> dict[str, Any]:
    phones = [c.value for c in lead.contacts if c.kind == "phone"]
    if not phones:
        return {"ok": False, "outcome": "no_phone"}

    suppression = suppression or SuppressionService(db)
    compliance = compliance or ComplianceService(suppression=suppression)
    check = compliance.check(
        channel="voice", phone=phones[0], campaign=campaign, db=db,
    )
    if not check.ok:
        return {"ok": False, "outcome": "blocked", "reason": compliance.block_reason_string(check)}

    provider = provider or MockVoiceProvider()
    script = CALL_SCRIPT.format(sender="Your Name", business=lead.name)
    req = CallRequest(
        phone=normalize_phone(phones[0]),
        script=script,
        lead_id=lead.id,
        sender_name="Your Name",
        ai_disclosed=True,
    )
    result = provider.place_call(req)

    call = Call(
        id=new_uuid(),
        lead_id=lead.id,
        provider_call_id=result.provider_call_id,
        dnc_checked_at=datetime.now(),
        ai_disclosed=True,
        outcome=result.outcome,
        transcript=result.transcript,
        recording_consent=result.recording_consent,
    )
    db.add(call)
    if result.success:
        lead.status = transition(lead.status, "contacted")
    db.commit()
    record(db, action="voice_call", lead_id=lead.id,
           detail={"outcome": result.outcome, "ok": result.success})
    return {"ok": result.success, "outcome": result.outcome}
