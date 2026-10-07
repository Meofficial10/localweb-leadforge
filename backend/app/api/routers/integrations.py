"""Integrations: status cards, encrypted secret set/meta, test-connection."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.core.audit import record
from app.core.crypto import set_secret, secret_meta
from app.db import get_session
from app.models.integration_secret import IntegrationSecret
import httpx

router = APIRouter(prefix="/integrations", tags=["integrations"])

INTEGRATION_KEYS = [
    "places.api_key",
    "llm.ollama.base_url",
    "llm.openai.api_key",
    "llm.anthropic.api_key",
    "hosting.cloudflare.api_key",
    "hosting.netlify.api_key",
    "email.smtp.password",
    "email.brevo.api_key",
    "email.resend.api_key",
    "voice.vapi.api_key",
    "voice.retell.api_key",
    "voice.bland.api_key",
    "dnc.registry.api_key",
]


class SecretSetRequest(BaseModel):
    key: str
    value: str


def _has_secret(db: Session, key: str) -> bool:
    row = db.query(IntegrationSecret).filter(IntegrationSecret.key == key).first()
    return row is not None


@router.get("")
def list_integrations(db: Session = Depends(get_session)):
    cards = [
        {"id": "places", "name": "Google Places", "kind": "source",
         "configured": bool(settings.places_api_key) or _has_secret(db, "places.api_key")},
        {"id": "osm", "name": "OSM Overpass", "kind": "source",
         "configured": bool(settings.osm_enabled)},
        {"id": "llm", "name": "LLM (" + settings.llm_provider + ")", "kind": "ai",
         "configured": settings.llm_provider != "mock",
         "detail": "provider=" + settings.llm_provider + " model=" + settings.llm_model},
        {"id": "hosting", "name": "Demo hosting (" + settings.hosting_provider + ")", "kind": "hosting",
         "configured": bool(settings.hosting_api_key) or _has_secret(db, "hosting.netlify.api_key") or _has_secret(db, "hosting.cloudflare.api_key")},
        {"id": "email", "name": "Email (" + settings.email_provider + ")", "kind": "email",
         "configured": settings.email_provider != "file"},
        {"id": "voice", "name": "Voice (" + settings.voice_provider + ")", "kind": "voice",
         "configured": settings.voice_provider != "mock"},
        {"id": "dnc", "name": "DNC registry (" + settings.dnc_provider + ")", "kind": "dnc",
         "configured": settings.dnc_provider != "none"},
    ]
    secrets = [secret_meta(db, k) for k in INTEGRATION_KEYS]
    return {"cards": cards, "secrets": secrets}


@router.post("/secrets")
def set_integration_secret(payload: SecretSetRequest, db: Session = Depends(get_session)):
    if payload.key not in INTEGRATION_KEYS:
        raise HTTPException(400, "unknown integration key")
    set_secret(db, payload.key, payload.value)
    record(db, action="integration_secret_set", detail={"key": payload.key})
    return secret_meta(db, payload.key)


@router.delete("/secrets/{key}")
def delete_integration_secret(key: str, db: Session = Depends(get_session)):
    row = db.query(IntegrationSecret).filter(IntegrationSecret.key == key).first()
    if row:
        db.delete(row)
        db.commit()
    return {"cleared": True}


class TestConnectionResult(BaseModel):
    ok: bool
    message: str = ""


def _probe(url: str, timeout: float = 10.0) -> bool:
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True)
        return r.status_code < 500
    except Exception:
        return False


@router.post("/{integration_id}/test", response_model=TestConnectionResult)
def test_connection(integration_id: str, db: Session = Depends(get_session)):
    if integration_id not in ("places", "osm", "llm", "hosting", "email", "voice", "dnc"):
        raise HTTPException(404, "unknown integration")
    try:
        if integration_id == "osm":
            ok = _probe(settings.overpass_base_url + "?data=%5Bout%3Ajson%5D%3Bnode(1)%3Bout%3B")
            return TestConnectionResult(ok=ok, message="Overpass reachable" if ok else "Overpass unreachable")
        if integration_id == "places":
            if not (settings.places_api_key or _has_secret(db, "places.api_key")):
                return TestConnectionResult(ok=False, message="No Places API key configured (free tier key needed)")
            return TestConnectionResult(ok=True, message="Credential present; live validation runs on first discovery")
        if integration_id == "llm":
            if settings.llm_provider == "mock":
                return TestConnectionResult(ok=True, message="Mock LLM always available")
            if settings.llm_provider == "ollama":
                ok = _probe(settings.ollama_base_url + "/api/tags")
                return TestConnectionResult(ok=ok, message="Ollama reachable" if ok else "Ollama unreachable at " + settings.ollama_base_url)
            has = bool(settings.openai_api_key or settings.anthropic_api_key)
            if not has:
                return TestConnectionResult(ok=False, message="No LLM API key configured")
            return TestConnectionResult(ok=True, message="Credential present; live validation runs on first request")
        if integration_id == "hosting":
            if settings.hosting_provider == "local":
                return TestConnectionResult(ok=True, message="Local file hosting always available")
            has = bool(settings.hosting_api_key or _has_secret(db, "hosting." + settings.hosting_provider + ".api_key"))
            if not has:
                return TestConnectionResult(ok=False, message="No hosting token configured")
            return TestConnectionResult(ok=True, message="Credential present; live validation runs on first deploy")
        if integration_id == "email":
            if settings.email_provider == "file":
                return TestConnectionResult(ok=True, message="File sender always available (dry-run outbox)")
            has = bool(settings.brevo_api_key or settings.resend_api_key or settings.smtp_password)
            if not has:
                return TestConnectionResult(ok=False, message="No email credentials configured")
            return TestConnectionResult(ok=True, message="Credential present; live validation runs on first send")
        if integration_id == "voice":
            if settings.voice_provider == "mock":
                return TestConnectionResult(ok=True, message="Mock voice provider always available")
            if not settings.voice_api_key:
                return TestConnectionResult(ok=False, message="No voice API key configured")
            return TestConnectionResult(ok=True, message="Credential present; live validation runs on first call")
        if integration_id == "dnc":
            if settings.dnc_provider == "none":
                return TestConnectionResult(ok=False, message="No DNC provider configured - voice stays fail-closed")
            return TestConnectionResult(ok=True, message="DNC provider configured")
        return TestConnectionResult(ok=False, message="unsupported")
    except HTTPException:
        raise
    except Exception as exc:
        return TestConnectionResult(ok=False, message="Error: " + str(exc))
