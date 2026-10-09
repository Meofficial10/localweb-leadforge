"""Resolve the configured LLM provider into a service that records every call into llm_calls.
Reads the live integrations config so the active model/provider match the Configure drawer."""
from __future__ import annotations

from app.core.settings_service import get_setting
from app.llm.mock import MockLLM
from app.llm.ollama import OllamaLLM
from app.llm.service import LLMService


def resolve_llm(db=None):
    """Return (LLMService, provider_id, model)."""
    provider = get_setting(db, "integration.llm.provider", "ollama") if db else "ollama"
    base_url = get_setting(db, "integration.llm.base_url", "http://localhost:11434") if db else "http://localhost:11434"
    from app.config import settings
    model = (get_setting(db, "integration.llm.model", "") or "") if db else ""
    if not model:
        model = settings.llm_model or "qwen2.5:3b"
    if provider == "ollama":
        inner = OllamaLLM(base_url=base_url, model=model)
    else:
        inner = MockLLM()
    svc = LLMService(provider=inner, model=model, provider_id=provider)
    return svc, provider, model
