"""M5: performance supporting endpoints."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import override_session_factory
from app.models.base import Base
from app.models.message import Message
from app.models.audit_log import AuditLog
from app.models.lead import Lead


def _mk_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TS = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    override_session_factory(TS)
    from app.main import app
    c = TestClient(app)
    return c, TS


def _seed(TS):
    with TS() as s:
        lead = Lead(id="lead-1", name="Dummy Co", source="osm", source_place_id="osm-chips:1", status="enriched", contact_type="email")
        s.add(lead)
        for i in range(1, 6):
            s.add(Message(id="msg-" + str(i), lead_id="lead-1", channel="email", direction="outbound", status="draft", subject="Subject " + str(i), body="body"))
        for i in range(1, 6):
            s.add(AuditLog(id=i, action="campaign_run", detail={"i": i}))
        s.commit()


def test_messages_paginated_envelope():
    c, TS = _mk_client()
    _seed(TS)
    r = c.get("/messages?page=1&page_size=2")
    assert r.status_code == 200
    b = r.json()
    assert sorted(b.keys()) == ["items", "page", "page_size", "total"]
    assert b["total"] == 5 and len(b["items"]) == 2 and b["page_size"] == 2
    flat = c.get("/messages?status=draft")
    assert isinstance(flat.json(), list) and len(flat.json()) == 5
    override_session_factory(None)


def test_messages_filter_status_channel():
    c, TS = _mk_client()
    _seed(TS)
    r = c.get("/messages?status=draft&channel=email")
    assert r.status_code == 200 and len(r.json()) == 5
    r2 = c.get("/messages?status=sent")
    assert r2.json() == []
    override_session_factory(None)


def test_audit_paginated_envelope():
    c, TS = _mk_client()
    _seed(TS)
    r = c.get("/system/audit?page=1&page_size=3")
    assert r.status_code == 200
    b = r.json()
    assert sorted(b.keys()) == ["items", "page", "page_size", "total"]
    assert b["total"] == 5 and len(b["items"]) == 3
    flat = c.get("/system/audit?limit=2")
    assert isinstance(flat.json(), list) and len(flat.json()) == 2
    override_session_factory(None)


def test_overview_combined_endpoint():
    c, TS = _mk_client()
    _seed(TS)
    r = c.get("/system/overview")
    assert r.status_code == 200
    b = r.json()
    assert sorted(b.keys()) == ["audit", "caps", "metrics", "status"]
    assert b["metrics"]["kpis"]["leads_found"] == 1
    assert b["status"]["force_dry_run"] is not None
    assert "daily_email_cap" in b["caps"]
    assert "daily_call_cap" in b["caps"]
    override_session_factory(None)


def test_overview_cached_repeat_call():
    c, TS = _mk_client()
    _seed(TS)
    a = c.get("/system/overview").json()
    b = c.get("/system/overview").json()
    assert a["metrics"]["kpis"]["leads_found"] == b["metrics"]["kpis"]["leads_found"]
    assert sorted(b.keys()) == ["audit", "caps", "metrics", "status"]
    override_session_factory(None)
