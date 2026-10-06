"""API smoke tests using FastAPI TestClient with an in-memory DB."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import settings  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # override the session dependency
    from app.db import get_session
    from app.main import create_app

    def override_get_session():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as tc:
        yield tc
    Base.metadata.drop_all(bind=engine)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_campaign_defaults_to_dry_run(client):
    assert settings.force_dry_run  # safety default on
    r = client.post("/campaigns", json={
        "name": "SG Cafes",
        "city": "Singapore",
        "categories": ["cafe"],
        "mode": "live",  # user requests live -> must be overridden in tests
    })
    if settings.force_dry_run:
        assert r.status_code == 200
        assert r.json()["mode"] == "dry_run"


def test_kill_switch(client):
    r = client.post("/system/pause", json={"paused": True})
    assert r.status_code == 200
    r2 = client.get("/system/status")
    assert r2.json()["paused"] is True


def test_suppression_endpoint(client):
    r = client.post("/suppression", json={"kind": "email", "value": "x@y.com", "reason": "test"})
    assert r.status_code == 200
    r2 = client.get("/suppression")
    assert any(item["value"] == "x@y.com" for item in r2.json())
