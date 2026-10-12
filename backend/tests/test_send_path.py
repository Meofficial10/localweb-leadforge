"""Workstream F: queue/outbox dry-run send path hardening tests.

The send path stays DRY-RUN: send_message() must (1) only accept approved/queued
messages that pass the compliance gate, and (2) drop any real provider adapter
down to the file outbox when dry-run is active (global force_dry_run OR campaign
mode dry_run). All fixtures are fake - no real businesses, emails or phones.
"""
from __future__ import annotations

from datetime import datetime

from app.config import settings
from app.core.compliance import ComplianceService
from app.core.suppression import SuppressionService
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.outreach.email.sender import SMTPMailer, SendResult
from app.utils import new_uuid


class ProbedSender:
    """Records something like an SMTP adapter trying to fire during a dry run."""
    def __init__(self):
        self.calls = []
    def send(self, **kw):
        self.calls.append(kw)
        return SendResult(success=True, provider_message_id="smtp:probed")


def _camp(db, mode="dry_run"):
    camp = Campaign(id=new_uuid(), name="F", city="Singapore", categories=["salon"],
                    mode=mode, daily_email_cap=20, daily_call_cap=10)
    db.add(camp); db.commit()
    return camp


def _lead(db, camp, email="owner@example.com", status="queued_email"):
    lead = Lead(id=new_uuid(), campaign_id=camp.id, source="fake", source_place_id="f1",
                name="Sample Dental Clinic", category="dental", has_website=False, status=status)
    db.add(lead)
    if email:
        db.add(Contact(lead_id=lead.id, kind="email", value=email, source_url="https://example.com/email", verified=False))
    db.commit()
    return lead


def _msg(db, lead, status="approved", provider=None):
    m = Message(id=new_uuid(), lead_id=lead.id, channel="email", direction="outbound",
                sequence_step=1, subject="Quick idea", body="Hi Sample, quick demo: https://example.com/demo",
                status=status, provider_message_id=provider)
    db.add(m); db.commit()
    return m


def test_send_approved_dry_run_goes_to_outbox(db, monkeypatch, tmp_path):
    camp = _camp(db)
    lead = _lead(db, camp)
    msg = _msg(db, lead, status="approved")
    from app.jobs.send import send_message
    # Point FileSender at a temp dir via monkeypatch on settings attribute database_url? No — that would change DB.
    # FileSender uses settings.database_dir which is derived from database_url. For the in-memory test,
    # it'd write to real backend/data/outbox. Instead replace the sender-with-SMTP probe to prove bypass? 
    # Simplest: monkeypatch FileSender.send to record, but we want an actual file proof.
    import app.outreach.email.sender as sender_mod
    real_file_sender = sender_mod.FileSender()
    captured = {}
    class FileProbe(sender_mod.FileSender):
        def send(self, **kw):
            r = super().send(**kw)
            captured.update(kw)
            return r
    res = send_message(db, msg, campaign=camp, sender=FileProbe())
    assert res["ok"] is True, res
    assert msg.status == "sent"
    assert lead.status == "contacted"
    assert msg.provider_message_id, "no provider id recorded"
    assert "file:" in msg.provider_message_id
    assert "no strings" not in (captured.get("body") or "")


def test_send_requires_approved_or_queued(db):
    camp = _camp(db)
    lead = _lead(db, camp)
    draft_msg = _msg(db, lead, status="draft")
    from app.jobs.send import send_message
    res = send_message(db, draft_msg, campaign=camp)
    assert res["ok"] is False
    assert "not sendable" in res["error"]


def test_send_blocked_by_suppression(db):
    camp = _camp(db)
    lead = _lead(db, camp, email="blocked@example.com")
    msg = _msg(db, lead, status="approved")
    sup = SuppressionService(db)
    sup.add("email", "blocked@example.com", reason="unsubscribe")
    from app.jobs.send import send_message
    res = send_message(db, msg, campaign=camp, suppression=sup)
    assert res["ok"] is False
    assert res["status"] == "blocked"
    assert msg.status == "approved", "blocked message must not be sent"


def test_dry_run_ignores_caller_smtp_adapter(db):
    """Even a NEVER-config'd hybrid: passing an SMTP-style adapter while dry-run is on
    must NOT fire it - the path pins to FileSender."""
    import app.jobs.send as send_mod
    from app.outreach.email.sender import FileSender
    camp = _camp(db, mode="dry_run")
    lead = _lead(db, camp)
    msg = _msg(db, lead, status="approved")
    class FakeReal:
        def send(self, **kw):
            raise AssertionError("a real provider must NOT fire in dry-run")
    # send_message only uses sender_file when NOT dry-run; here it should ignore ours
    probe = ProbedSender()
    res = send_mod.send_message(db, msg, campaign=camp, sender=probe)
    assert res["ok"] is True
    assert probe.calls == [], "passed-in adapter was used during dry-run - MUST be ignored"
    assert msg.status == "sent"


def test_send_live_mode_uses_passed_sender(db):
    """Live mode (force_dry_run off) allowed - but only with an explicit sender,
    still gated by compliance (no suppression)."""
    import app.jobs.send as send_mod
    from app.main import app
    camp = _camp(db, mode="live")
    lead = _lead(db, camp)
    msg = _msg(db, lead, status="approved")
    probe = ProbedSender()
    # override global force_dry_run for this test via monkeypatch
    monkeypatch = __import__("pytest").MonkeyPatch()
    monkeypatch.setattr(settings, "force_dry_run", False)
    try:
        res = send_mod.send_message(db, msg, campaign=camp, sender=probe,
                                    suppression=SuppressionService(db))
    finally:
        monkeypatch.undo()
    # live mode + no suppression + provided SMTP adapter: it should go out via probe
    assert res["ok"] is True, res
    assert len(probe.calls) == 1
    assert msg.status == "sent"


def test_outbox_endpoint_lists_sent_files(db, tmp_path, monkeypatch):
    """GET /queue/outbox surfaces status=sent messages with the file sink id."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_session
    from app.api.routers import queue as queue_router
    camp = _camp(db)
    lead = _lead(db, camp)
    msg = _msg(db, lead, status="approved")
    # simulate the send step writing a sent message with a file provider id
    msg.status = "sent"
    msg.provider_message_id = "file:outbox_sent_1.eml"
    msg.sent_at = datetime(2025, 1, 1, 12, 0, 0)
    db.commit()

    def override_get_session():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as c:
            r = c.get("/queue/outbox")
            assert r.status_code == 200, r.text
            items = r.json()
            assert any(it["id"] == msg.id for it in items), items
            sent_item = next(it for it in items if it["id"] == msg.id)
            assert sent_item["provider_message_id"] == "file:outbox_sent_1.eml"
            assert sent_item["status"] == "sent"
            assert sent_item["lead_name"] == "Sample Dental Clinic"
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_queue_send_endpoint_rejects_unapproved(db):
    """POST /queue/{id}/send on a draft is rejected with 409, nothing is sent."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_session
    camp = _camp(db)
    lead = _lead(db, camp)
    draft_msg = _msg(db, lead, status="draft")

    def override_get_session():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as c:
            r = c.post(f"/queue/{draft_msg.id}/send")
            assert r.status_code == 409, r.text
            assert draft_msg.status == "draft"
    finally:
        app.dependency_overrides.pop(get_session, None)
