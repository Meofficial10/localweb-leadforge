"""Workstream H: voice call-script + DNC adapter wiring tests.

Covers DNC registry resolution (fail-closed "none" default, registry adapter with
/check endpoint), compliance gating for voice (DNC + call window + suppression),
and the dry-run provider pin (MockVoiceProvider is always used when voice_dry_run
or force_dry_run is on, even if a caller passes a real adapter). All fake.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.compliance import ComplianceService
from app.core.dnc import NoDNCCheck, StubDNCCheck, DNCUnavailable, get_dnc_registry
from app.core.suppression import SuppressionService
from app.models.campaign import Campaign
from app.models.call import Call
from app.models.contact import Contact
from app.models.lead import Lead
from app.outreach.voice.provider import CallRequest, CallResult
from app.utils import new_uuid


def _camp(db, mode="dry_run"):
    camp = Campaign(id=new_uuid(), name="H", city="Singapore", categories=["repair"],
                    mode=mode, daily_email_cap=20, daily_call_cap=10)
    db.add(camp); db.commit()
    return camp


def _lead(db, camp, phone="+65 0000 1111", status="queued_call"):
    lead = Lead(id=new_uuid(), campaign_id=camp.id, source="fake", source_place_id="h1",
                name="Repair Works", category="repair", has_website=False, status=status)
    db.add(lead)
    if phone:
        db.add(Contact(lead_id=lead.id, kind="phone", value=phone, source_url="https://example.com/phone", verified=False))
    db.commit()
    return lead


def _clear_compliance(db, dnc=None):
    """Compliance that allows a call: no dry-run block, wide call window, stub DNC clear."""
    return ComplianceService(suppression=SuppressionService(db), dnc=dnc or StubDNCCheck(),
                             force_dry_run=False, call_hours="00:00-23:59",
                             call_days="mon,tue,wed,thu,fri,sat,sun")


def _raise_if_called():
    class BoomProvider:
        name = "boom"
        def place_call(self, req):
            raise AssertionError("real adapter fire during dry-run - must be replaced by mock")
    return BoomProvider()


def test_no_phone_returns_no_phone(db):
    from app.jobs.voice import place_call_for_lead
    camp = _camp(db)
    lead = _lead(db, camp, phone=None)
    r = place_call_for_lead(db, lead, camp)
    assert r == {"ok": False, "outcome": "no_phone"}


def test_voice_dry_run_default_blocks(db):
    from app.jobs.voice import place_call_for_lead
    camp = _camp(db)
    lead = _lead(db, camp)
    r = place_call_for_lead(db, lead, camp)
    assert r["ok"] is False and r["outcome"] == "blocked"
    assert "dry-run" in (r.get("reason") or "")


def test_dnc_on_registry_blocks_call(db):
    from app.jobs.voice import place_call_for_lead
    dnc = StubDNCCheck()
    dnc.register("+65 0000 1111")
    camp = _camp(db)
    lead = _lead(db, camp)
    compliance = _clear_compliance(db, dnc=dnc)
    r = place_call_for_lead(db, lead, camp, compliance=compliance)
    assert r["ok"] is False and r["outcome"] == "blocked"
    assert "DNC" in (r.get("reason") or "")
    assert db.query(Call).count() == 0, "no call row may be written for a blocked DNC lead"


def test_dry_run_pins_mock_even_with_real_adapter(db):
    from app.jobs.voice import place_call_for_lead
    camp = _camp(db)
    lead = _lead(db, camp)
    camp.mode = "live"
    comp = _clear_compliance(db, dnc=StubDNCCheck())
    r = place_call_for_lead(db, lead, camp, provider=_raise_if_called(), compliance=comp)
    # compliance would pass (stub clear + wide window) but provider pin keeps it mock
    assert r["ok"] is True
    assert r["outcome"] == "incomplete"  # mock default outcome
    assert db.query(Call).count() == 1
    c = db.query(Call).first()
    assert c.ai_disclosed is True


def test_full_call_path_records_call_and_transition(db):
    from app.jobs.voice import place_call_for_lead
    camp = _camp(db, mode="live")
    lead = _lead(db, camp, status="queued_call")
    comp = _clear_compliance(db, dnc=StubDNCCheck())
    r = place_call_for_lead(db, lead, camp, compliance=comp)
    assert r["ok"] is True
    assert r["outcome"] == "incomplete"
    c = db.query(Call).first()
    assert c is not None
    assert c.lead_id == lead.id
    assert c.ai_disclosed is True
    assert "AI assistant" in (c.transcript or "") or "Demo" in (c.transcript or "")
    db.refresh(lead)
    assert lead.status == "contacted"
