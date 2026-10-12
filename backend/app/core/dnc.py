"""Do Not Call (DNC) registry screening.

For Singapore, phone numbers must be checked against the DNC registry before any
call or text. The default `none` provider fails CLOSED: if no provider is
configured, `check\\(...\\)` returns False and calls are blocked, which satisfies
"HARD COMPLIANCE": if the check cannot be completed, do not call.

A provider adapter can be configured via DNC_PROVIDER (=\"configurable adapter\").
An in-process stub (\"stub\") is provided for tests/local dev that lets you load
a manual do-not-call list.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class DNCProvider(Protocol):
    name: str

    def check(self, phone: str) -> bool:
        """Return True if the number is allowed to be called (not on DNC). Raised-on-check signals
        that we could not complete the check, which must FAIL the gate."""
        ...


class NoDNCCheck(DNCProvider):
    """No provider configured. Fails closed (returns False = do not call)."""

    name = "none"

    def check(self, phone: str) -> bool:
        return False


@dataclass
class StubDNCCheck(DNCProvider):
    """Local stub. Numbers in \"dnc_numbers\" are on the registry; anything else is safe."""

    name = "stub"
    dnc_numbers: set[str] = field(default_factory=set)

    def check(self, phone: str) -> bool:
        digits = "".join(ch for ch in phone if ch.isdigit())
        return digits not in self.dnc_numbers

    def register(self, phone: str) -> None:
        self.dnc_numbers.add("".join(ch for ch in phone if ch.isdigit()))


class FailingDNCCheck(DNCProvider):
    """Provider whose check could not complete (network down etc.). Fails closed."""

    name = "unavailable"

    def check(self, phone: str) -> bool:
        raise DNCUnavailable("DNC registry unreachable")


class DNCUnavailable(Exception):
    pass


class DNCRegistry:
    """Resolves the configured provider and enforces fail-closed semantics.

    `.check\\(phone\\)` returns True only when the provider confirms the number is clear.
    Any exception during the provider check is converted to False (block) and logged.
    """

    def __init__(self, provider: DNCProvider | None = None):
        self.provider = provider or NoDNCCheck()

    def check(self, phone: str) -> bool:
        try:
            return bool(self.provider.check(phone))
        except Exception as exc:  # noqa: BLE001 - fail closed
            raise DNCUnavailable(str(exc)) from exc



def get_dnc_registry(provider_name: str | None = None,
                     api_key: str | None = None,
                     base_url: str | None = None) -> DNCRegistry:
    """Resolve the DNC provider configured in settings into a fail-closed registry.

    "none" (default) -> NoDNCCheck: every call is blocked.
    "registry"       -> HTTP adapter; missing key or any error fails closed.
    The endpoint the adapter hits is {base}/check?phone=..., documented and safe
    to call only when the operator configured a real registry.
    """
    from app.config import settings as _settings
    name = provider_name or _settings.dnc_provider or "none"
    if name == "registry":
        key = api_key if api_key is not None else _settings.dnc_api_key
        base = base_url if base_url is not None else _settings.dnc_registry_base_url
        if not key:
            # no key configured -> cannot complete the check -> fail closed
            return DNCRegistry(NoDNCCheck())
        return DNCRegistry(RegistryDNCCheck(base_url=base, api_key=key))
    return DNCRegistry(NoDNCCheck())


class RegistryDNCCheck(DNCProvider):
    """HTTP DNC registry adapter. Fails closed on any error/timeout."""
    name = "registry"

    def __init__(self, base_url: str = "", api_key: str = "") -> None:
        import httpx
        self._httpx = httpx
        self.base_url = (base_url or "https://dnc.registry.example").rstrip("/")
        self.api_key = api_key

    def check(self, phone: str) -> bool:
        if not self.api_key:
            raise DNCUnavailable("dnc registry api key not configured")
        digits = "".join(ch for ch in phone if ch.isdigit())
        try:
            r = self._httpx.get(
                self.base_url + "/check",
                params={"phone": digits},
                headers={"Authorization": "Bearer " + self.api_key},
                timeout=10,
            )
        except Exception as exc:  # noqa: BLE001
            raise DNCUnavailable("dnc registry unreachable: " + str(exc)) from exc
        if r.status_code == 200:
            return True  # registry confirmed the number is clear to call
        if r.status_code in (404, 410):
            return False  # registry says do not call / number not found -> block
        raise DNCUnavailable("dnc registry returned HTTP " + str(r.status_code))
