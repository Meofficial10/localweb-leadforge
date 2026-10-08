"""Mocked-HTTP tests for the truthful connection probes.

Each probe runs through app.core.integrations.test_integration with httpx
patched so no real network is touched. Covers success, auth failure,
timeout and unreachable-host outcomes.
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest import mock

from app.core import integrations as ig

"""Actually no triple-docstring inside single-quoted Python lines - keep it simple"""

sys_path_bootstrap = "import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"

from unittest import mock

from app.core import integrations as ig


def _session():
    from sqlalchemy import create_engine, orm, pool
    from app.models.base import Base
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=pool.StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = orm.sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return Session()


class FakeResponse:
    status_code = 200
    def __init__(self, status_code=200, json_data=None, text="", exc=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text
        self.exc = exc
    def _raise(self):
        if self.exc is not None:
            raise self.exc
        return self
    def json(self):
        return self._json
    def raise_for_status(self):
        if self.status_code >= 400:
            raise ValueError(str(self.status_code))


def _patch_get(resp):
    def fake_get(url, **kwargs):
        return resp._raise()
    return mock.patch.object(ig.httpx, "get", fake_get)


def _patch_post(resp):
    def fake_post(url, **kwargs):
        return resp._raise()
    return mock.patch.object(ig.httpx, "post", fake_post)


# ---------- LLM ----------

def test_ollama_success():
    db = _session()
    ok = {"models": [{"name": "qwen2.5:7b"}, {"name": "llama3.2:3b"}]}
    with _patch_get(FakeResponse(200, ok)):
        r = ig.test_integration(db, "llm", {"provider": "ollama", "base_url": "http://x", "model": "qwen2.5:7b"})
    assert r["ok"] is True
    assert "Ollama" in r["message"]
    assert "qwen2.5:7b" in r["detail"]


def test_ollama_wrong_url_fails():
    db = _session()
    with _patch_get(FakeResponse(404, {}, text="page not found")):
        r = ig.test_integration(db, "llm", {"provider": "ollama", "base_url": "http://127.0.0.1:9999"})
    assert r["ok"] is False
    assert "Ollama" in r["message"] or "not running" in r["message"]


def test_ollama_unreachable():
    db = _session()
    with _patch_get(FakeResponse(exc=OSError("connection refused"))):
        r = ig.test_integration(db, "llm", {"provider": "ollama", "base_url": "http://127.0.0.1:11434"})
    assert r["ok"] is False
    assert "Ollama" in r["message"]


def test_ollama_timeout():
    db = _session()
    with _patch_get(FakeResponse(exc=TimeoutError("timed out"))):
        r = ig.test_integration(db, "llm", {"provider": "ollama", "base_url": "http://127.0.0.1:11434"})
    assert r["ok"] is False
    assert "Ollama" in r["message"] or "reach" in r["message"] or "timed" in r["message"]


def test_openai_success():
    db = _session()
    ok = {"object": "list", "data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}
    with _patch_get(FakeResponse(200, ok)):
        r = ig.test_integration(db, "llm", {"provider": "openai", "api_key": "sk-test", "base_url": "https://api.openai.com/v1"})
    assert r["ok"] is True
    assert "OpenAI" in r["message"]


def test_openai_auth_failure():
    db = _session()
    with _patch_get(FakeResponse(401, {}, text="unauthorized")):
        r = ig.test_integration(db, "llm", {"provider": "openai", "api_key": "sk-bad", "base_url": "https://api.openai.com/v1"})
    assert r["ok"] is False
    assert "rejected" in r["message"].lower() or "401" in r["message"]


# ---------- Places ----------

def test_places_success():
    db = _session()
    body = {"candidates": [{"name": "Bluewater Salon", "formatted_address": "123 Main St"}], "status": "OK"}
    with _patch_get(FakeResponse(200, body)):
        r = ig.test_integration(db, "places", {"api_key": "fakekey"})
    assert r["ok"] is True
    assert "Bluewater" in r["detail"]


def test_places_invalid_key():
    db = _session()
    body = {"status": "REQUEST_DENIED", "status_message": "This IP is not authorized"}
    with _patch_get(FakeResponse(200, body)):
        r = ig.test_integration(db, "places", {"api_key": "bad-key"})
    assert r["ok"] is False
    assert "Places" in r["message"] or "Places" in r.get("detail", "")


# ---------- Hosting ----------

def test_cloudflare_success():
    db = _session()
    with _patch_get(FakeResponse(200, {"success": True})):
        r = ig.test_integration(db, "hosting", {"provider": "cloudflare", "api_key": "tok", "base_url": "https://api.cloudflare.com/client/v4"})
    assert r["ok"] is True


def test_netlify_success():
    db = _session()
    with _patch_get(FakeResponse(200, {"slug": "me"})):
        r = ig.test_integration(db, "hosting", {"provider": "netlify", "api_key": "tok", "base_url": "https://api.netlify.com/api/v1"})
    assert r["ok"] is True

