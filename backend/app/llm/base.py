"""Provider-agnostic LLM interface. All providers implement generate(prompt, schema).

The schema is a JSON schema; outputs are validated against it and rejected on
mismatch (this is the guard that prevents hallucinated facts from reaching emails).
"""
from __future__ import annotations

from typing import Any, Protocol


class LLMUnavailable(Exception):
    pass


class LLMSchemaError(Exception):
    pass


class LLMProvider(Protocol):
    name: str

    def generate(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return validated JSON for the given schema. Raises LLMSchemaError on invalid output."""
        ...
