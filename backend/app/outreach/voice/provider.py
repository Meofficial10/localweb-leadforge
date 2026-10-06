"""Voice provider adapter interface. All providers (Vapi/Retell/Bland + mock)
share one interface. The mock provider logs the call script and returns an outcome,
never placing a real call (dry-run default).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from app.config import settings


@dataclass
class CallRequest:
    phone: str
    script: str
    lead_id: str
    sender_name: str
    ai_disclosed: bool = True


@dataclass
class CallResult:
    success: bool
    outcome: str = ""
    transcript: str = ""
    recording_consent: bool = False
    provider_call_id: str | None = None
    error: str | None = None


class VoiceProvider(Protocol):
    name: str

    def place_call(self, req: CallRequest) -> CallResult:
        ...


class MockVoiceProvider(VoiceProvider):
    """Dry-run voice provider: logs the script, returns a canned outcome, never calls."""

    name = "mock"

    def __init__(self, outcome: str = "incomplete", consent: bool = False):
        self.outcome = outcome
        self.consent = consent

    def place_call(self, req: CallRequest) -> CallResult:
        if not req.ai_disclosed:
            return CallResult(success=False, error="ai_disclosed must be true")
        return CallResult(
            success=True,
            outcome=self.outcome,
            transcript=f"[mock] Called {req.phone}. Script: {req.script[:120]}...",
            recording_consent=self.consent,
            provider_call_id=f"mock-{int(time.time())}",
        )


def get_voice_provider(provider: str | None = None) -> VoiceProvider:
    provider = provider or settings.voice_provider
    if provider == "mock":
        return MockVoiceProvider()
    raise NotImplementedError(f"{provider} adapter not wired - use mock for dry-run")
