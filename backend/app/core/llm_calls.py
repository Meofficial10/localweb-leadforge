"""LLM call recorder: every generation writes a row to llm_calls so the AI activity
page can show what the system generated, with which provider/model, latency and
token usage. Purely writes when a session is present; never raises."""
from __future__ import annotations

from app.models.llm_call import LLMCall


def record_llm_call(db, *, purpose, provider, model, latency_ms=None, tokens=None,
                     status="ok", error=None, prompt="", response="",
                     run_id=None, lead_id=None):
    if db is None:
        return None
    try:
        tokens = tokens or {}
        call = LLMCall(
            run_id=run_id, lead_id=lead_id, purpose=purpose, provider=provider,
            model=model, latency_ms=latency_ms,
            prompt_tokens=tokens.get("prompt"), completion_tokens=tokens.get("completion"),
            total_tokens=tokens.get("total"), status=status, error=(error or None),
            prompt=str(prompt)[:20000], response=str(response)[:20000],
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call.id
    except Exception as exc:
        try:
            db.rollback()
        except Exception:
            pass
        return None
