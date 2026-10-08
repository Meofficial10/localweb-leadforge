"""M4: campaign wizard support — offline location dataset endpoints + wizard payload validation."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import override_session_factory
from app.models.base import Base



def _mk_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TS = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    override_session_factory(TS)
    from app.main import app
    c = TestClient(app)
    return c, TS


def test_locations_countries():
    c, TS = _mk_client()
    r = c.get("/locations/countries")
    assert r.status_code == 200
    countries = r.json()["countries"]
    assert any(x["code"] == "SG" and "flag" in x and x["name"] == "Singapore" for x in countries)
    override_session_factory(None)


def test_locations_states_and_cities():
    c, TS = _mk_client()
    st = c.get("/locations/SG/states")
    assert st.status_code == 200 and st.json()["states"] == ["Singapore"]
    ci = c.get("/locations/SG/cities?state=Singapore")
    assert ci.status_code == 200
    cities = ci.json()["cities"]
    for want in ["Orchard", "Bukit Timah", "Tampines", "Jurong East", "Toa Payoh"]:
        assert want in cities, f"missing SG planning area {want}"
    # unknown country -> 404, no network calls
    assert c.get("/locations/ZZ/cities").status_code == 404
    override_session_factory(None)


def test_wizard_validate_missing_steps():
    c, TS = _mk_client()
    r = c.post("/campaigns/validate", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["step1"]["ok"] is False and any("name" in e for e in body["step1"]["errors"])
    assert body["step1"]["ok"] is False and any("source" in e for e in body["step1"]["errors"])
    assert body["step2"]["ok"] is False and any("city" in e for e in body["step2"]["errors"])
    assert body["step3"]["ok"] is False and any("business" in e for e in body["step3"]["errors"])
    override_session_factory(None)


def test_wizard_validate_complete_passes():
    c, TS = _mk_client()
    r = c.post("/campaigns/validate", json={
        "name": "Queensway Clinics",
        "lead_sources": ["google", "apify"],
        "city": "Singapore",
        "towns": ["Orchard", "Bukit Timah"],
        "categories": ["clinic"],
        "channels": ["email"],
    })
    assert r.status_code == 200
    b = r.json()
    assert all(b[k]["ok"] for k in ("step1", "step2", "step3", "step4")), b
    override_session_factory(None)


def test_campaign_create_with_wizard_fields():
    c, TS = _mk_client()
    r = c.post("/campaigns", json={
        "name": "Wizard Campaign",
        "city": "Singapore",
        "country": "SG",
        "categories": ["salon"],
        "lead_sources": ["google", "osm"],
        "description": "from the 4-step wizard",
        "channels": ["email", "voice"],
        "budget_cap": 25.5,
    })
    assert r.status_code == 200
    d = r.json()
    assert d["description"] == "from the 4-step wizard"
    assert d["channels"] == ["email", "voice"]
    assert d["budget_cap"] == 25.5
    assert d["lead_sources"] == ["google", "osm"]
    assert d["mode"] == "dry_run"  # force-dry-run enforced
    override_session_factory(None)