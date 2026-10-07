"""Integrations: catalog cards with per-provider fields, encrypted secrets,
test connections, model listing, and the "X of Y required integrations working" health summary."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import integrations as _ig
from app.core.audit import record
from app.core.crypto import set_secret, secret_meta
from app.db import get_session

router = APIRouter(prefix="/integrations", tags=["integrations"])


class SecretSetRequest(BaseModel):
    key: str
    value: str


class ConfigureRequest(BaseModel):
    values: dict


def _card(db: Session, integ: _ig.IntegrationDef) -> dict:
    c = _ig.cfg(db, integ)
    st = _ig.status(db, integ)
    prov = _ig.provider_for(db, integ)
    secret = None
    if prov is not None and prov.needs_key and _ig._is_key_set(db, prov.key_secret_key):
        secret = secret_meta(db, prov.key_secret_key)
    return {
        "id": integ.id, "name": integ.name, "kind": integ.kind, "required": integ.required,
        "description": integ.description,
        "providers": [p.to_dict() for p in integ.providers],
        "fields": [f.to_dict() for f in integ.fields],
        "provider": c.get("provider"),
        "config": c,
        "status": st,
        "secret": secret,
    }


# secrets known by the catalog (provider-specific) plus legacy-compat keys
def _known_secret_keys() -> set:
    known = {p.key_secret_key for i in _ig.INTEGRATIONS for p in i.providers if p.needs_key}
    known |= {"email.smtp.password"}  # provider key already covers it
    return known


@router.get("")
def list_integrations(db: Session = Depends(get_session)):
    cards = [_card(db, i) for i in _ig.INTEGRATIONS]
    return {"cards": cards, "health": _ig.health_summary(db),
            "required_ids": _ig.REQUIRED_IDS, "force_dry_run": True}


@router.post("/{integration_id}/configure")
def configure_integration(integration_id: str, payload: ConfigureRequest,
                          db: Session = Depends(get_session)):
    try:
        cfg = _ig.save_config(db, integration_id, payload.values)
    except KeyError:
        raise HTTPException(404, "unknown integration")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    record(db, action="integration_configured", detail={"id": integration_id})
    result = _ig.test_integration(db, integration_id)  # auto-test after save
    return {"config": cfg, "test": result}


@router.post("/{integration_id}/test")
def test_connection(integration_id: str, db: Session = Depends(get_session)):
    if integration_id not in _ig.CATALOG:
        raise HTTPException(404, "unknown integration")
    return _ig.test_integration(db, integration_id)


@router.get("/{integration_id}/models")
def list_models(integration_id: str, provider: str = "ollama",
                base_url: str = "", db: Session = Depends(get_session)):
    if integration_id != "llm" or provider not in _ig.LLM_PROVIDER_MAP:
        return {"models": []}
    return {"models": _ig.llm_model_list(db, provider, base_url or None)}


@router.post("/secrets")
def set_integration_secret(payload: SecretSetRequest, db: Session = Depends(get_session)):
    known = _known_secret_keys()
    if payload.key not in known:
        raise HTTPException(400, "unknown integration key")
    set_secret(db, payload.key, payload.value)
    record(db, action="integration_secret_set", detail={"key": payload.key})
    return secret_meta(db, payload.key)


@router.delete("/secrets/{key}")
def delete_integration_secret(key: str, db: Session = Depends(get_session)):
    from app.models.integration_secret import IntegrationSecret
    row = db.query(IntegrationSecret).filter(IntegrationSecret.key == key).first()
    if row:
        db.delete(row)
        db.commit()
    return {"cleared": True}
