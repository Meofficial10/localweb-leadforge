"""Workstream C — demo site quality tests.

Checks the 8 theme packs, required page sections, no external requests, noindex,
page weight < 100KB, accessible markup, and that no unverified claim reaches the
rendered page.
"""
from __future__ import annotations

import pytest

from app.build.templates import (
    THEMES,
    all_themes,
    render_demo_site,
    theme_for_category,
)

REALISH_SENDER = "sender@example.net"


def _profile():
    return {
        "summary": "A friendly local business serving the local area.",
        "services": [
            {"text": "Book an appointment", "kind": "generic", "source_fact_id": None},
            {"text": "Visit us today", "kind": "generic", "source_fact_id": None},
            {"text": "Concern: optics"}, {"text": "Contact us"},
        ],
        "selling_points": [],
        "brand": {"colors": ["#3B5BDB", "#F7F8FA", "#1F2430"], "theme": "generic"},
    }


def _biz(**over):
    biz = {
        "name": "Sample Dental Clinic",
        "address": "1 Demo Road",
        "category": "dentist",
        "phone": "+65 0000 0000",
        "email": "owner@example.com",
        "opening_hours": "Mon-Fri 9am-6pm",
    }
    biz.update(over)
    return biz


def test_eight_theme_packs():
    keys = [t["key"] for t in all_themes()]
    assert len(keys) >= 8
    for expected in ("clinical", "salon", "cafe", "boutique", "repair", "education", "fitness", "generic"):
        assert expected in keys


def test_theme_for_category_maps_categories():
    assert theme_for_category("Dental clinic") == "clinical"
    assert theme_for_category("hair salon") == "salon"
    assert theme_for_category("cafe") == "cafe"
    assert theme_for_category("auto repair") == "repair"
    assert theme_for_category("fitness gym") == "fitness"
    assert theme_for_category("tuition") == "education"
    assert theme_for_category("boutique") == "boutique"
    assert theme_for_category("") == "generic"


def test_required_sections_present():
    html = render_demo_site(_profile(), _biz(), sender=REALISH_SENDER)
    for token in (
        "<header", "site-header", "class=\"hero\"", "id=\"main\"",
        "h-services", "h-about", "h-why", "h-contact", "<footer>",
        "noindex,nofollow", "skip-link",
    ):
        assert token in html, f"missing {token}"


def test_phone_buttons_and_no_unverified_claims():
    html = render_demo_site(_profile(), _biz(), sender=REALISH_SENDER)
    assert "tel:+6500000000" in html
    assert "wa.me/6500000000" in html
    assert "Sample content" in html  # services are generic, not verified -> labelled sample block


def test_placeholder_sender_identity():
    html = render_demo_site(_profile(), _biz(sender_hidden=True), sender="sender@example.net")
    assert "samples.net" in html or "Demo preview by" in html


def test_page_under_100kb():
    html = render_demo_site(_profile(), _biz(), sender=REALISH_SENDER)
    assert len(html) < 100_000


def test_no_external_requests():
    html = render_demo_site(_profile(), _biz(), sender=REALISH_SENDER)
    for token in ("http://", "https://fonts", "<script", "gtag(", "analytics", "facebook.com", "<iframe"):
        assert token not in html, f"forbidden token {token}"


# --- demo management endpoints + expiry (Workstream C) ---

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_session
from app.main import create_app
from app.models import Base as _ModelsBase
from app.models.demo_site import DemoSite
from app.models.lead import Lead
from app.models.campaign import Campaign
from app.models.profile import Profile
from app.utils import new_uuid


def _mk():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    _ModelsBase.metadata.create_all(bind=engine)
    TS = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_session():
        s = TS()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    c = TestClient(app)
    return c, TS, app


def _seed(c, TS):
    camp = c.post("/campaigns", json={"name": "Demo QA", "city": "Testville", "mode": "dry_run"})
    camp_id = camp.json()["id"]
    with TS() as s:
        lead = Lead(id=new_uuid(), campaign_id=camp_id, source="seed", source_place_id="seed-demo1",
                    name="Sample Clinic", category="dentist", address="1 Demo Road", status="demo_ready",
                    has_website=False, contact_type="phone")
        s.add(lead)
        s.add(Profile(lead_id=lead.id, summary="A friendly clinic.", services=["Book an appointment"],
                     selling_points=["Visit us today"]))
        s.add(DemoSite(id=new_uuid(), lead_id=lead.id, template="clinical", html_path=None,
                       preview_url="/demos/sample-1/", deploy_status="live"))
        lead_id = lead.id
        s.commit()
    return lead_id


def _teardown(engine):
    engine.dispose()


def test_demo_delete_endpoint():
    c, TS, app = _mk()
    try:
        lead = _seed(c, TS)
        r = c.post(f"/demos/{lead}/delete")
        assert r.status_code == 200 and r.json()["deleted"] >= 1
        with TS() as s:
            assert s.query(DemoSite).filter(DemoSite.lead_id == lead).count() == 0
    finally:
        _ModelsBase.metadata.drop_all(bind=create_engine) if False else None
        # dispose is handled by GC; leave engine


def test_demo_build_log_endpoint():
    c, TS, app = _mk()
    lead = _seed(c, TS)
    r = c.get(f"/demos/{lead}/build_log")
    assert r.status_code == 200
    body = r.json()
    assert body["deploy_status"] == "live"
    assert body["template"] == "clinical"
    assert "expired" in body
    assert isinstance(body["facts"], list)


def test_demo_theme_switch_endpoint():
    c, TS, app = _mk()
    lead = _seed(c, TS)
    r = c.patch(f"/demos/{lead}/theme", json={"template": "salon"})
    assert r.status_code == 200
    assert r.json()["template"] == "salon"


def test_demo_theme_unknown_rejected():
    c, TS, app = _mk()
    lead = _seed(c, TS)
    r = c.patch(f"/demos/{lead}/theme", json={"template": "no-such-theme"})
    assert r.status_code == 400


def test_demo_expiry_logic():
    from datetime import datetime, timedelta
    from app.api.routers.demos import demo_expired
    class FakeSite:
        def __init__(self, created):
            self.created_at = created
    fresh = FakeSite(datetime.now() - timedelta(days=5))
    old = FakeSite(datetime.now() - timedelta(days=40))
    assert not demo_expired(fresh)
    assert demo_expired(old)
