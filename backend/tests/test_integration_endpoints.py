"""M2: integration endpoints — model list fetch and Apify token validation (mocked)."""
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
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    override_session_factory(TestSession)
    from app.main import app
    c = TestClient(app)
    yield c, monkeypatch
    override_session_factory(None)


class FakeResp:
    status_code = 200
    def __init__(self, payload=None):
        self.payload = payload or {}
    def json(self):
        return self.payload
    def raise_for_status(self):
        pass


def test_llm_models_ollama(client):
    c, mp = client
    import httpx
    def fake_get(url, timeout=20, **kw):
        return FakeResp({"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.1:8b"}]})
    mp.setattr("httpx.get", fake_get)
    r = c.get("/integrations/llm/models", params={"provider": "ollama", "base_url": "http://localhost:11434"})
    assert r.status_code == 200
    models = r.json()["models"]
    assert "qwen2.5:7b" in models and "llama3.1:8b" in models


def test_apify_token_valid(client):
    c, mp = client
    sr = c.post("/integrations/secrets", json={"key": "apify.api_token", "value": "apify_token_abc"})
    assert sr.status_code == 200
    import httpx
    def fake_get(url, params=None, timeout=30):
        assert params and params.get("token") == "apify_token_abc", "should pass the real token"
        return FakeResp({"data": {"username": "test_user"}})
    mp.setattr("httpx.get", fake_get)
    r = c.post("/integrations/apify/test")
    # this uses the real validate_token against mocked httpx.get