"""Workstream G: follow-up + reply/bounce tracking tests.

Covers scheduling (follow-ups are never immediate, they carry scheduled_at =
now + days_delay), cancel-on-response (a reply/opt-out/bounce cancels any
pending step-2 draft), and webhook tracking of replies/bounces with state
transitions that stay consistent with the state machine. All fixtures fake.
"""
from __future__ import annotations

import datetime as _dt


from app.core.state_machine import can_transition, transition
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.utils import new_uuid


def _camp(db, mode="dry_run"):
    camp = Campaign(id=new_uuid(), name="G", city="Singapore", categories=["dental"],
                    mode=mode, daily_email_cap=20, daily_call_cap=10)
    db.add(camp); db.commit()
    return camp


def _lead(db, camp, email="owner@example.com", status="contacted"):
    lead = Lead(id=new_uuid(), campaign_id=camp.id, source="fake", source_place_id="g1",
                name="Sample Dental Clinic", category="dental", has_website=False, status=status)
    db.add(lead)
    if (email):
        db.add(Contact(lead_id=lead.id, kind="email", value=email, source_url="https://example.com/email", verified=False))
    db.commit()
    return lead


def _sent_email(db, lead, step=1):
    m = Message(id=new_uuid(), lead_id=lead.id, channel="email", direction="outbound",
                sequence_step=step, subject="Quick idea" if step == 1 else "Following up",
                body="Hi, demo here: https://example.com/demo", status="sent")
    db.add(m); db.commit()
    return m


def test_schedule_followup_is_deferred_and_scheduled(db):
    from app.jobs.send import schedule_followup
    camp = _camp(db)
    lead = _lead(db, camp)
    _sent_email(db, lead)
    follow = schedule_followup(db, lead, camp, days_delay=4)
    assert follow is not None
    assert follow.sequence_step == 2
    assert follow.status == "draft", "follow-up must stay a draft"
    assert follow.scheduled_at is not None, "follow-up must carry a scheduled time"
    assert follow.scheduled_at > _dt.datetime.utcnow()
    assert lead.status == "followup_sent"


def test_followup_only_once(db):
    from app.jobs.send import schedule_followup
    camp = _camp(db)
    lead = _lead(db, camp)
    _sent_email(db, lead)
    first = schedule_followup(db, lead, camp, days_delay=4)
    second = schedule_followup(db, lead, camp, days_delay=4)
    assert first is not None
    assert second is None
    step2 = [m for m in lead.messages if m.sequence_step == 2]
    assert len(step2) == 1


def test_no_followup_after_reply(db):
    from app.jobs.send import schedule_followup
    camp = _camp(db)
    lead = _lead(db, camp)
    _sent_email(db, lead)
    # simulate an inbound reply already present
    db.add(Message(id=new_uuid(), lead_id=lead.id, channel="email", direction="inbound",
                   sequence_step=1, subject="Re: Quick idea", inbound_content="Sounds good, let's chat",
                   status="replied", intent="interested"))
    db.commit()
    follow = schedule_followup(db, lead, camp, days_delay=4)
    assert follow is None, "must not schedule a follow-up after the lead replied"


def test_reply_webhook_cancels_pending_followup(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_session
    camp = _camp(db)
    lead = _lead(db, camp)
    sent = _sent_email(db, lead)
    # a pending follow-up draft exists (e.g. created by scheduling, not yet sent)
    pending = Message(id=new_uuid(), lead_id=lead.id, channel="email", direction="outbound",
                      sequence_step=2, subject="Following up", body="Hi, demo: https://example.com/demo",
                      status="draft")
    db.add(pending); db.commit()

    def override_get_session():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as c:
            r = c.post("/webhooks/email", json={
                "event": "reply",
                "email": "owner@example.com",
                "message_id": sent.id,
                "body": "yes I'm interested, this looks great",
            })
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["action"] == "replied"
            assert data["intent"] == "interested"
            db.refresh(pending)
            assert pending.status == "cancelled", "pending follow-up should be cancelled"
            db.refresh(lead)
            assert lead.status == "replied"
            db.refresh(sent)
            assert sent.status == "replied"
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_bounce_webhook_tracks_and_cancels(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_session
    from app.core.settings_service import get_setting
    camp = _camp(db)
    lead = _lead(db, camp)
    sent = _sent_email(db, lead)
    pending = Message(id=new_uuid(), lead_id=lead.id, channel="email", direction="outbound",
                      sequence_step=2, subject="Following up", body="Hi, demo", status="draft")
    db.add(pending); db.commit()

    def override_get_session():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides_removed = False
    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as c:
            r = c.post("/webhooks/email", json={
                "event": "bounce",
                "email": "owner@example.com",
                "message_id": sent.id,
            })
            assert r.status_code == 200, r.text
            assert r.json()["handled"] is True
            db.refresh(sent)
            assert sent.bounced is True
            db.refresh(lead)
            assert lead.status == "bounced"
            db.refresh(pending)
            assert pending.status == "cancelled"
            # auto-pause stats
            assert float(get_setting(db, "stats.bounce_rate", 0.0) or 0.0) > 0
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_unsubscribe_webhook_suppresses_and_cancels(db):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_session
    camp = _camp(db)
    lead = _lead(db, camp)
    sent = _sent_email(db, lead)
    pending = Message(id=new_uuid(), lead_id=lead.id, channel="email", direction="outbound",
                      sequence_step=2, subject="Following up", body="Hi, demo", status="draft")
    db.add(pending); db.commit()

    def override_get_session():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as c:
            r = c.post("/webhooks/email", json={"event": "unsubscribe", "email": "owner@example.com"})
            assert r.status_code == 200, r.text
            assert r.json()["action"] == "suppressed"
            db.refresh(pending)
            assert pending.status == "cancelled"
            db.refresh(lead)
            assert lead.status == "opted_out"
    finally:
        app.dependency_overrides.pop(get_session, None)
