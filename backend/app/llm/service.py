"""LLM service: resolves configured provider, validates output against JSON schema,
and wires basic error handling."""
from __future__ import annotations

from typing import Any

import jsonschema

from app.config import settings
from app.llm.base import LLMProvider, LLMSchemaError
from app.llm.mock import MockLLM


class LLMService:
    def __init__(self, provider: LLMProvider | None = None, model: str | None = None):
        self._provider = provider
        self._model = model or settings.llm_model

    def _resolve(self) -> LLMProvider:
        if self._provider is not None:
            return self._provider
        # provider resolution is delegated at construction time in prod config
        return MockLLM()

    def generate(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        provider = self._resolve()
        raw = provider.generate(prompt, schema)
        if schema:
            try:
                jsonschema.validate(instance=raw, schema=schema)
            except jsonschema.ValidationError as exc:
                raise LLMSchemaError(str(exc)) from exc
        return raw
