"""LLM service: resolves configured provider, validates output against JSON schema,
records every call into llm_calls, and wires basic error handling."""
from __future__ import annotations

import time
from typing import Any

import jsonschema

from app.config import settings
from app.core.llm_calls import record_llm_call
from app.llm.base import LLMProvider, LLMSchemaError
from app.llm.mock import MockLLM


class LLMService:
    def __init__(self, provider=None, model=None, provider_id="mock", db=None,
                 purpose="profile", run_id=None, lead_id=None, active=False):
        self._provider = provider
        self._model = model or settings.llm_model
        self.provider_id = provider_id or "mock"
        self.db = db
        self.purpose = purpose
        self.run_id = run_id
        self.lead_id = lead_id
        self.active = active
        if self._provider is None:
            self._provider = self._resolve()

    def _resolve(self):
        if self._provider is not None:
            return self._provider
        return MockLLM()

    def generate(self, prompt, schema=None):
        provider = self._provider
        t0 = time.monotonic()
        error = None
        raw = None
        status = "ok"
        tokens = None
        try:
            raw = provider.generate(prompt, schema)
        except Exception as exc:
            error = str(exc)
            status = "error"
            raise
        finally:
            latency = int((time.monotonic() - t0) * 1000)
            lp = getattr(provider, "last_payload", {}) or {}
            tokens = lp.get("tokens") or tokens
            resp_text = lp.get("response") or (str(raw) if raw is not None else "")
            record_llm_call(self.db, purpose=self.purpose, provider=self.provider_id,
                            model=self._model, latency_ms=latency, tokens=tokens,
                            status=status, error=error, prompt=prompt, response=resp_text,
                            run_id=self.run_id, lead_id=self.lead_id)
        if schema:
            try:
                jsonschema.validate(instance=raw, schema=schema)
            except jsonschema.ValidationError as exc:
                from app.llm.base import LLMSchemaError
                raise LLMSchemaError(str(exc)) from exc
        return raw

    @property
    def model(self):
        return self._model
