"""AI activity: what the LLM generated, with which provider/model, latency, tokens.
Backs the /ai-activity page and the Playground in the Configure drawer."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import integrations as _ig
from app.core.llm_calls import record_llm_call
from app.db import get_session
from app.llm.ollama import OllamaLLM

router = APIRouter(prefix="/ai", tags=["ai"])


def _row(c) -> dict:
    return {
        "id": c.id, "run_id": c.run_id, "lead_id": c.lead_id, "purpose": c.purpose,
        "provider": c.provider, "model": c.model, "latency_ms": c.latency_ms,
        "prompt_tokens": c.prompt_tokens, "completion_tokens": c.completion_tokens,
        "total_tokens": c.total_tokens, "status": c.status, "error": c.error,
        "prompt": c.prompt, "response": c.response,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }

@router.get("/activity")
def ai_activity(db: Session = Depends(get_session)):
    from app.models.llm_call import LLMCall
    today = datetime.now(timezone.utc) - timedelta(hours=24)
    recent = db.execute(
        select(LLMCall).order_by(LLMCall.id.desc()).limit(100)
    ).scalars().all()
    total = db.query(func.count(LLMCall.id)).scalar() or 0
    today_rows = db.execute(
        select(LLMCall).where(LLMCall.created_at >= today)
    ).scalars().all()
    fails = [c for c in today_rows if c.status == "error"]
    lat = [c.latency_ms for c in today_rows if c.latency_ms is not None]
    provider = _ig.get_setting(db, "integration.llm.provider", "ollama")
    model = _ig.get_setting(db, "integration.llm.model", "") or ""
    return {
        "calls_today": len(today_rows),
        "failures_today": len(fails),
        "avg_latency_ms": int(sum(lat) / len(lat)) if lat else None,
        "total_calls": total,
        "calls": [_row(c) for c in recent],
        "active": {"provider": provider, "model": model},
    }


class PlaygroundRequest(BaseModel):
    prompt: str
    model: str = ""
    base_url: str = ""


@router.post("/playground")
def ai_playground(payload: PlaygroundRequest, db: Session = Depends(get_session)):
    model = payload.model.strip() or "qwen2.5:3b"
    base = payload.base_url.strip() or "http://localhost:11434"
    import time
    t0 = time.perf_counter()
    try:
        out = OllamaLLM(base_url=base, model=model)
        lp = getattr(out, "last_payload", {}) or {}
        raw = out.generate(payload.prompt, None) if hasattr(out, "generate") else None
        latency = int((time.perf_counter() - t0) * 1000)
        text = lp.get("response") or ""
        if not text and isinstance(raw, dict):
            text = raw.get("content") or ""
        elif not text and isinstance(raw, str):
            text = raw
        tokens = lp.get("tokens") or {}
        record_llm_call(db, purpose="playground", provider="ollama", model=model,
                        latency_ms=latency, tokens=tokens, status="ok",
                        prompt=payload.prompt, response=text)
        return {"ok": True, "reply": text, "latency_ms": latency, "tokens": tokens,
                "model": model, "at": datetime.now(timezone.utc).isoformat()}
    except Exception as exc:
        record_llm_call(db, purpose="playground", provider="ollama", model=model,
                        status="error", error=str(exc), prompt=payload.prompt, response="")
        return {"ok": False, "error": str(exc), "at": datetime.now(timezone.utc).isoformat()}
