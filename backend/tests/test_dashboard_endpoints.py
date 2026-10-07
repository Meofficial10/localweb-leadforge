"""Tests for the dashboard-upgrade backend endpoints:
campaign CRUD, effective mode enforcement, queue, inbox, integrations/secrets, settings."""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import override_session_factory
from app.models.base import Base


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    # override the factory used by get_session
    override_session_factory(TestSession)

    from app.main import app
    from app.api.routers import campaigns, queue, inbox
    # keep already-bound routers working against the new DB
    from fastapi.testclient import TestClient as TC
    c = TC(app)
    yield c
    override_session_factory(None)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["force_dry_run"] is True


def test_create_campaign_forces_dry_run(client):
    r = client.post("/campaigns", json={
        "name": "T1", "city": "Singapore", "categories": ["salon"], "mode": "live",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "dry_run"
    cid = body["id"]
    # read back
    assert client.get("/campaigns/" + cid).json()["name"] == "T1"
    # update
    up = client.patch("/campaigns/" + cid, json={"city": "Jurong", "mode": "live"})
    assert up.json()["mode"] == "dry_run"  # force wins
    assert up.json()["city"] == "Jurong"
    # duplicate
    dup = client.post("/campaigns/" + cid + "/duplicate").json()
    assert dup["is_paused"] is True
    assert dup["mode"] == "dry_run"
    # delete
    assert client.delete("/campaigns/" + cid).json()["deleted"] is True


def test_status_effective_mode_never_live(client):
    st = client.get("/system/status").json()
    assert st["force_dry_run"] is True
    assert st["channels"]["email"]["effective_mode"] == "dry_run"
    assert st["channels"]["voice"]["effective_mode"] == "dry_run"


def test_metrics_shape(client):
    m = client.get("/system/metrics").json()
    for key in ("leads_found", "with_contact", "demos_built", "emails_drafted", "emails_sent", "replies"):
        assert key in m["kpis"]
    assert "funnel" in m and "leads_per_day" in m


def test_integrations_secrets_masked(client):
    r = client.get("/integrations")
    assert r.status_code == 200
    assert len(r.json()["cards"]) == 7
    secrets = r.json()["secrets"]
    assert all(s["masked"] == "" for s in secrets if not s["is_set"])
    # set a secret
    setr = client.post("/integrations/secrets", json={"key": "email.brevo.api_key", "value": "BKEY-secret-1234"})
    assert setr.status_code == 200
    body = setr.json()
    assert body["is_set"] is True
    assert "KEY-secret-" not in body["masked"]  # never expose value
    assert body["masked"].endswith("1234")
    # test connection
    tres = client.post("/integrations/email/test")
    assert tres.json()["ok"] is True or tres.json()["message"] != ""
    # clear
    clr = client.delete("/integrations/secrets/email.brevo.api_key")
    assert clr.json()["cleared"] is True


def test_settings_and_delete_request(client):
    s = client.get("/settings").json()
    assert "budgets" in s and "branding" in s and "tokens" in s
    # update defaults
    p = client.patch("/settings", json={"values": {"daily_email_cap": 15}})  # v ? 
    assert p.status_code == 200
    # data deletion request suppresses + records
    dr = client.post("/settings/delete-request", json={"email": "someone@example.com"})
    assert dr.json()["requested"] is True
    # now the email is suppressed
    lr = client.get("/suppression?search=someone@example.com").json()
    assert any(x["value"] == "someone@example.com" for x in lr)
    # suppression CSV export
    exp = client.get("/suppression/export.csv")
    assert exp.status_code == 200 and "kind,value" in exp.text
    # remove suppression
    sid = next(x["id"] for x in lr if x["value"] == "someone@example.com")
    rm = client.delete("/suppression/" + sid, params={"reason": "removed in test"})
    assert rm.json()["removed"] is True


def test_campaign_runs_did_not_use_old_pause_path(client):
    # patch pause endpoint still works (query param shape)
    camp = client.post("/campaigns", json={"name":"P1","city":"SG","categories":["cafe"]}).json()
    p = client.patch("/campaigns/" + camp["id"] + "/pause", params={"paused": True})
    assert p.json()["is_paused"] is True

def test_lead_detail_serializer_enriched(client):
    """Lead detail includes contact, message timeline and calls (drawer data)."""
    from app.models.lead import Lead
    from app.models.contact import Contact
    from app.models.message import Message
    from app.models.call import Call
    from app.db import get_sync_session

    s = get_sync_session()
    lead = Lead(source="google_maps", source_place_id="enrich-1", name="Enrich Co",
                category="salon", address="2 Orchard Rd", contact_type="email")
    s.add(lead); s.flush()
    s.add(Contact(lead_id=lead.id, kind="email", value="hi@enrich.example.com"))
    s.add(Message(lead_id=lead.id, channel="email", direction="outbound", status="draft",
                  subject="Hello Enrich Co", sequence_step=1))
    s.add(Call(lead_id=lead.id, outcome="no_answer", ai_disclosed=True, duration_sec=12))
    s.commit(); s.expire_all()
    lid = lead.id
    s.close()

    det = client.get("/leads/" + lid).json()
    assert any(c["value"] == "hi@enrich.example.com" for c in det["contacts"])
    assert det["messages"] and "channel" in det["messages"][0] and det["messages"][0]["channel"] == "email"
    assert det["calls"] and det["calls"][0]["ai_disclosed"] is True
    assert "profile" in det
