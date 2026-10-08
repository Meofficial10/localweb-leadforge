"""Integration catalog: provider metadata, config storage, status + test connections.

Config for each integration lives in the `settings` table (non-secret fields)
and `integration_secrets` (API keys, encrypted at rest). Because the tests in
this file only *read* settings/secrets the module is import-safe for unit tests.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Callable

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.core.crypto import get_secret, set_secret, secret_meta
from app.core.settings_service import get_setting, set_setting

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ProviderDef:
    __slots__ = ("id", "label", "needs_key", "key_secret_key", "base_url_default",
                 "base_url_editable", "static_models", "probe_url", "note")

    def __init__(self, id: str, label: str, *, needs_key: bool = False,
                 key_secret_key: str | None = None, base_url_default: str = "",
                 base_url_editable: bool = False, static_models: list[str] | None = None,
                 probe_url: str | None = None, note: str = "") -> None:
        self.id = id
        self.label = label
        self.needs_key = needs_key
        self.key_secret_key = key_secret_key or (id + ".api_key")
        self.base_url_default = base_url_default
        self.base_url_editable = base_url_editable
        self.static_models = static_models or []
        self.probe_url = probe_url
        self.note = note

    def to_dict(self) -> dict:
        return {
            "id": self.id, "label": self.label, "needs_key": self.needs_key,
            "key_secret_key": self.key_secret_key, "base_url_default": self.base_url_default,
            "base_url_editable": self.base_url_editable, "static_models": self.static_models,
            "probe_url": self.probe_url, "note": self.note,
        }


class FieldDef:
    __slots__ = ("key", "label", "type", "placeholder", "help", "options", "default")

    def __init__(self, key: str, label: str, *, type: str = "text",
                 placeholder: str = "", help: str = "", options: list[str] | None = None,
                 default: Any = None) -> None:
        self.key = key
        self.label = label
        self.type = type
        self.placeholder = placeholder
        self.help = help
        self.options = options
        self.default = default

    def to_dict(self) -> dict:
        return {"key": self.key, "label": self.label, "type": self.type,
                "placeholder": self.placeholder, "help": self.help,
                "options": self.options, "default": self.default}


class IntegrationDef:
    __slots__ = ("id", "name", "kind", "required", "description", "providers",
                 "fields", "provider_key", "enable_key", "enabled_by_default")

    def __init__(self, id: str, name: str, kind: str, *, required: bool = False,
                 description: str = "", providers: list[ProviderDef] | None = None,
                 fields: list[FieldDef] | None = None, provider_key: str | None = None,
                 enable_key: str | None = None, enabled_by_default: bool = True) -> None:
        self.id = id
        self.name = name
        self.kind = kind
        self.required = required
        self.description = description
        self.providers = providers or []
        self.fields = fields or []
        self.provider_key = provider_key or f"integration.{id}.provider"
        self.enable_key = enable_key or f"integration.{id}.enabled"
        self.enabled_by_default = enabled_by_default

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "kind": self.kind, "required": self.required,
            "description": self.description,
            "providers": [p.to_dict() for p in self.providers],
            "fields": [f.to_dict() for f in self.fields],
            "provider_key": self.provider_key, "enable_key": self.enable_key,
            "enabled_by_default": self.enabled_by_default,
        }


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

LLM_PROVIDERS = [
    ProviderDef("ollama", "Ollama (local)", base_url_default="http://localhost:11434",
                base_url_editable=True, static_models=["qwen2.5:7b", "llama3.1:8b", "mistral:7b", "phi3:mini"],
                probe_url="/api/tags", note="Free, local. No API key."),
    ProviderDef("openai", "OpenAI", needs_key=True, key_secret_key="llm.openai.api_key",
                base_url_default="https://api.openai.com/v1", static_models=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]),
    ProviderDef("anthropic", "Anthropic", needs_key=True, key_secret_key="llm.anthropic.api_key",
                base_url_default="https://api.anthropic.com/v1", static_models=["claude-3-5-sonnet-20240620", "claude-3-haiku-20240307"]),
    ProviderDef("openrouter", "OpenRouter", needs_key=True, key_secret_key="llm.openrouter.api_key",
                base_url_default="https://openrouter.ai/api/v1", note="Aggregates many models."),
    ProviderDef("groq", "Groq", needs_key=True, key_secret_key="llm.groq.api_key",
                base_url_default="https://api.groq.com/openai/v1", static_models=["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]),
    ProviderDef("together", "Together", needs_key=True, key_secret_key="llm.together.api_key",
                base_url_default="https://api.together.xyz/v1"),
    ProviderDef("lmstudio", "LM Studio (local)", base_url_default="http://localhost:1234/v1",
                base_url_editable=True, note="Free, local, OpenAI-compatible."),
    ProviderDef("custom", "Custom (OpenAI-compatible)", needs_key=True,
                key_secret_key="llm.custom.api_key", base_url_default="https://your-endpoint.example/v1",
                base_url_editable=True, note="Any OpenAI-compatible /v1 endpoint."),
    ProviderDef("mock", "Mock (demo)", note="Canned, random responses — NO real LLM. Demo only."),
]

HOSTING_PROVIDERS = [
    ProviderDef("local", "Local file hosting", note="Free, writes to backend/data/demo_sites."),
    ProviderDef("cloudflare_pages", "Cloudflare Pages", needs_key=True,
                key_secret_key="hosting.cloudflare.api_key", base_url_default="https://api.cloudflare.com/client/v4",
                note="Needs an account API token with Pages edit scope."),
    ProviderDef("netlify", "Netlify", needs_key=True, key_secret_key="hosting.netlify.api_key",
                base_url_default="https://api.netlify.com/api/v1", note="Needs a site + Personal Access Token."),
]

EMAIL_PROVIDERS = [
    ProviderDef("file", "Local file sink (dry-run)", note="Writes .eml to backend/data/outbox."),
    ProviderDef("smtp", "SMTP", needs_key=True, key_secret_key="email.smtp.password",
                base_url_editable=True,
                note="Host/port/user under SMTP fields."),
    ProviderDef("brevo", "Brevo (Sendinblue)", needs_key=True, key_secret_key="email.brevo.api_key",
                static_models=None, note="Free tier."),
    ProviderDef("resend", "Resend", needs_key=True, key_secret_key="email.resend.api_key", note="Free tier."),
]

VOICE_PROVIDERS = [
    ProviderDef("vapi", "Vapi", needs_key=True, key_secret_key="voice.vapi.api_key",
                base_url_default="https://api.vapi.ai"),
    ProviderDef("retell", "Retell", needs_key=True, key_secret_key="voice.retell.api_key",
                base_url_default="https://api.retellai.com"),
    ProviderDef("bland", "Bland AI", needs_key=True, key_secret_key="voice.bland.api_key",
                base_url_default="https://api.bland.ai"),
    ProviderDef("custom", "Custom (OpenAI-compatible)", needs_key=True, key_secret_key="voice.custom.api_key",
                base_url_default="https://your-voice-endpoint.example", base_url_editable=True),
    ProviderDef("mock", "Mock (demo)", note="Returns a canned transcript. Demo only — NOT a real service."),
]

DNC_PROVIDERS = [
    ProviderDef("none", "No DNC provider", note="Voice stays fail-closed (blocks calls)."),
    ProviderDef("registry", "Registry API", needs_key=True, key_secret_key="dnc.registry.api_key",
                base_url_default="", base_url_editable=True),
]

INTEGRATIONS: list[IntegrationDef] = [
    IntegrationDef("llm", "LLM writer", "ai", required=True,
                   description="Writes personalised profiles and outreach drafts.",
                   providers=LLM_PROVIDERS,
                   fields=[
                       FieldDef("model", "Model", type="model",
                                placeholder="e.g. qwen2.5:7b (or select and edit)"),
                       FieldDef("temperature", "Temperature", type="number",
                                help="0 (deterministic) to 1 (creative). Visualise first.", default=0.3),
                       FieldDef("max_tokens", "Max tokens", type="number", default=1200),
                       FieldDef("timeout_sec", "Request timeout (s)", type="number", default=60),
                       FieldDef("fallback_provider", "Fallback provider", type="provider",
                                help="Used if the primary provider fails."),
                       FieldDef("headers", "Extra headers (JSON, optional)", type="textarea",
                                help="Custom headers for OpenAI-compatible providers, e.g. {\"X-Org\": \"acme\"}. Only used by Custom."),
                   ]),
    IntegrationDef("places", "Google Places", "source", required=False,
                   description="Official Places TextSearch + Details API (needs a key).",
                   providers=[
                       ProviderDef("official", "Official API", needs_key=True,
                                   key_secret_key="places.api_key",
                                   note="Never scrapes HTML. TextSearch + Details."),
                   ]),
    IntegrationDef("osm", "OpenStreetMap / Overpass", "source", required=False,
                   description="Free Overpass API fallback. Custom endpoint URL editable.",
                   providers=[
                       ProviderDef("overpass", "Overpass", base_url_default=settings.overpass_base_url,
                                   base_url_editable=True, note="Set a mirror endpoint if the public one is slow."),
                   ]),
    IntegrationDef("apify", "Apify", "source", required=False,
                   description="Runs a Google-Maps scraper actor and imports leads.",
                   providers=[
                       ProviderDef("apify", "Apify", needs_key=True, key_secret_key="apify.api_token"),
                   ],
                   fields=[
                       FieldDef("actor_id", "Actor ID", default="dSCLg0N4nXrK6omlg",
                                help="Default: free 'google-maps-scraper' actor. Editable."),
                       FieldDef("max_results", "Max results per run", type="number", default=100),
                       FieldDef("timeout_sec", "Run timeout (s)", type="number", default=300),
                       FieldDef("monthly_budget_cap", "Monthly budget cap (US$)", type="number", default=10.0),
                   ]),
    IntegrationDef("hosting", "Demo hosting", "hosting", required=False,
                   description="Where generated demo sites are deployed.",
                   providers=HOSTING_PROVIDERS),
    IntegrationDef("email", "Email sender", "email", required=True,
                   description="Sends outreach email (dry-run by default).",
                   providers=EMAIL_PROVIDERS,
                   fields=[
                       FieldDef("smtp_host", "SMTP host", type="text", placeholder="smtp.example.com"),
                       FieldDef("smtp_port", "SMTP port", type="number", default=587),
                       FieldDef("smtp_user", "SMTP username", type="text"),
                   ]),
    IntegrationDef("identity", "Sender identity", "identity", required=True,
                   description="The identity shown on outbound email (CAN-SPAM physical address).",
                   providers=[ProviderDef("identity", "Identity", base_url_editable=False)],
                   fields=[
                       FieldDef("sender_name", "Sender name", type="text"),
                       FieldDef("sender_email", "Sender email", type="email"),
                       FieldDef("physical_address", "Physical address", type="textarea"),
                       FieldDef("sender_phone", "Sender phone", type="text"),
                   ]),
    IntegrationDef("voice", "Voice calls", "voice", required=False,
                   description="AI voice outreach (dry-run by default).",
                   providers=VOICE_PROVIDERS),
    IntegrationDef("dnc", "DNC registry", "dnc", required=False,
                   description="Do-Not-Call check. If unavailable, voice stays fail-closed.",
                   providers=DNC_PROVIDERS),
]

CATALOG = {i.id: i for i in INTEGRATIONS}
LLM_PROVIDER_MAP = {p.id: p for p in LLM_PROVIDERS}
REQUIRED_IDS = [i.id for i in INTEGRATIONS if i.required]  # llm, email, identity


def catalog() -> list[dict]:
    return [i.to_dict() for i in INTEGRATIONS]


# ---------------------------------------------------------------------------
# Config / status helpers
# ---------------------------------------------------------------------------

def cfg(db: Session, integ: IntegrationDef) -> dict:
    """Read effective config for an integration."""
    out: dict[str, Any] = {
        "enabled": bool(get_setting(db, integ.enable_key, integ.enabled_by_default)),
        "provider": get_setting(db, integ.provider_key, (integ.providers[0].id if integ.providers else "")),
    }
    # provider-level overrides
    pid = out["provider"]
    prov = next((p for p in integ.providers if p.id == pid), None)
    if prov is not None:
        out["base_url"] = get_setting(db, f"integration.{integ.id}.base_url", prov.base_url_default)
    else:
        out["base_url"] = ""
    # generic fields
    for fd in integ.fields:
        key = f"integration.{integ.id}.{fd.key}"
        default = fd.default
        out[fd.key] = convert(get_setting(db, key, default))
    return out


def convert(v: Any) -> Any:
    # normalize settings numbers so the UI always gets sensible types
    if isinstance(v, str) and v.replace('.', '', 1).isdigit():
        return int(v) if v.count('.') == 0 else float(v)
    return v




def provider_for(db: Session, integ: IntegrationDef) -> ProviderDef:
    pid = get_setting(db, integ.provider_key, integ.providers[0].id if integ.providers else "")
    return next((p for p in integ.providers if p.id == pid), None) or (integ.providers[0] if integ.providers else None)


def _is_key_set(db: Session, key) -> bool:
    return secret_meta(db, key)["is_set"]


def has_required_fields(db: Session, integ: IntegrationDef) -> bool:
    prov = provider_for(db, integ)
    if prov is None or prov.id in ("none", "mock", "local", "file"):
        return True
    if prov.id == "identity":
        # sender identity needs at least a name/email to be "configured"
        return bool(get_setting(db, "integration.identity.sender_name", ""))
    if prov.needs_key and not _is_key_set(db, prov.key_secret_key):
        return False
    if prov.base_url_editable and not get_setting(db, f"integration.{integ.id}.base_url", ""):
        return False
    if integ.id == "email" and prov.id == "smtp" and not get_setting(db, "integration.email.smtp_host", ""):
        return False
    return True


def missing_fields(db: Session, integ: IntegrationDef) -> list[str]:
    out: list[str] = []
    prov = provider_for(db, integ)
    if prov is None:
        return ["no provider selected"]
    if prov.id not in ("none", "mock", "local", "file", "identity"):
        if prov.needs_key and not _is_key_set(db, prov.key_secret_key):
            out.append(prov.label + " API key")
        if prov.base_url_editable and not get_setting(db, f"integration.{integ.id}.base_url", ""):
            out.append("Base URL")
    if integ.id == "email" and prov.id == "smtp":
        if not get_setting(db, "integration.email.smtp_host", ""):
            out.append("SMTP host")
    return out



def status(db: Session, integ: IntegrationDef) -> dict:
    """Compute the card's status: one of disabled | not_configured | configured | connected | error."""
    c = cfg(db, integ)
    if not c["enabled"]:
        return {"state": "disabled", "label": "Disabled", "color": "gray", "icon": "toggle",
                "detail": "Integration is toggled off.", "last_checked": None}
    if not has_required_fields(db, integ):
        missing = missing_fields(db, integ)
        return {"state": "not_configured", "label": "Not configured", "color": "gray",
                "icon": "plug", "detail": "Missing: " + (", ".join(missing) or "configuration"),
                "last_checked": None}
    last = get_setting(db, f"integration.{integ.id}.last_test", None)
    if not last:
        return {"state": "configured", "label": "Configured, untested", "color": "yellow",
                "icon": "clock", "detail": "Credentials saved — run Test connection to verify.",
                "last_checked": None}
    if last.get("ok"):
        return {"state": "connected", "label": "Connected", "color": "green",
                "icon": "check", "detail": last.get("detail") or last.get("message", "Connection verified."),
                "last_checked": last.get("at")}
    return {"state": "error", "label": "Error", "color": "red", "icon": "x",
            "detail": (last.get("message", "Test failed.") + " " + (last.get("fix_hint") or "")).strip(),
            "last_checked": last.get("at")}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_config(db: Session, integ_id: str, payload: dict) -> dict:
    """Persist integration config. API keys go to the encrypted store."""
    integ = CATALOG.get(integ_id)
    if integ is None:
        raise KeyError(integ_id)
    if "provider" in payload:
        if not any(p.id == payload["provider"] for p in integ.providers):
            raise ValueError("unknown provider: " + str(payload["provider"]))
        set_setting(db, integ.provider_key, payload["provider"])
    if "enabled" in payload:
        set_setting(db, integ.enable_key, bool(payload["enabled"]))
    prov = provider_for(db, integ)
    for key_name in ("api_key", "secret_key", "token"):
        if key_name in payload and prov is not None and prov.needs_key and payload[key_name]:
            set_secret(db, prov.key_secret_key, str(payload[key_name]))
    base_url = payload.get("base_url")
    if base_url is not None and prov is not None and prov.base_url_editable:
        set_setting(db, f"integration.{integ_id}.base_url", str(base_url).strip())
    for fd in integ.fields:
        if fd.key in payload:
            set_setting(db, f"integration.{integ_id}.{fd.key}", payload[fd.key])
    set_setting(db, f"integration.{integ_id}.last_test", None)  # re-verify on next test
    return cfg(db, integ)


# ---------------------------------------------------------------------------
# Test connections
# ---------------------------------------------------------------------------

def _record_test(db: Session, integ_id: str, result: dict) -> dict:
    now = _now()
    result["at"] = now
    set_setting(db, f"integration.{integ_id}.last_test", result)
    return result


def _probe(db: Session, integ_id: str, url: str, ok_msg: str, err_msg: str = "") -> dict:
    t0 = time.perf_counter()
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True)
        latency = int((time.perf_counter() - t0) * 1000)
        ok = r.status_code < 500
        detail = f"{ok_msg} — {latency} ms" if ok else f"{err_msg or ok_msg} (HTTP {r.status_code})"
        return _record_test(db, integ_id, {"ok": ok, "message": ok_msg if ok else (err_msg or ok_msg),
                                            "detail": detail, "latency_ms": latency,
                                            "fix_hint": "" if ok else "Verify the endpoint URL and network access."})
    except Exception as exc:
        return _record_test(db, integ_id, {"ok": False, "message": err_msg or ("Error: " + str(exc)),
                                            "detail": str(exc), "fix_hint": "Verify the endpoint URL is reachable."})


TEST_TIMEOUT = 10.0  # seconds for every real connection probe


def _effective(db: Session, integ: IntegrationDef, values) -> dict:
    """Resolve the config actually in use, overlaying transient form values.
    `values` holds what the user currently typed (not yet saved). It never
    persists: testing unsaved state uses it; saved status comes only from storage.
    """
    v = values or {}
    prov = provider_for(db, integ)
    if v.get("provider") and any(p.id == v["provider"] for p in integ.providers):
        prov = next((p for p in integ.providers if p.id == v["provider"]), prov)
    cfgv = cfg(db, integ)
    base = v.get("base_url") or cfgv.get("base_url") or prov.base_url_default or ""
    key = v.get("api_key") or (get_secret(db, prov.key_secret_key) if prov.needs_key else None) or ""
    model = v.get("model") or cfgv.get("model") or (prov.static_models[0] if prov.static_models else "")
    smtp_host = v.get("smtp_host") or cfgv.get("smtp_host") or ""
    smtp_port = v.get("smtp_port") if v.get("smtp_port") is not None else cfgv.get("smtp_port") or 587
    smtp_user = v.get("smtp_username") or cfgv.get("smtp_username") or ""
    smtp_pass = v.get("smtp_password") or get_secret(db, prov.key_secret_key) or ""
    headers = v.get("headers") or cfgv.get("headers") or {}
    if isinstance(headers, str):
        import json
        try:
            headers = json.loads(headers) if headers.strip() else {}
        except Exception:
            headers = {}
    return {"prov": prov, "base": base.rstrip("/"), "key": key, "model": model,
            "smtp": {"host": smtp_host, "port": smtp_port, "user": smtp_user, "pass": smtp_pass},
            "headers": headers}


def _llm_headers(key: str, headers) -> dict:
    h = {"Content-Type": "application/json"}
    for k, v in (headers or {}).items():
        h[str(k)] = str(v)
    if key:
        h["Authorization"] = "Bearer " + key
    return h

def _test_llm(db, eff):
    base, key, model = eff["base"], eff["key"], eff["model"]
    prov = eff["prov"]
    try:
        if prov.id == "ollama":
            t0 = time.perf_counter()
            r = httpx.get(base + "/api/tags", timeout=TEST_TIMEOUT)
            latency = int((time.perf_counter() - t0) * 1000)
            if r.status_code != 200:
                return _record_test(db, "llm", {"ok": False,
                                                 "message": "Ollama not running at " + (base or "http://localhost:11434"),
                                                 "detail": "GET /api/tags -> HTTP " + str(r.status_code),
                                                 "fix_hint": "start it with: ollama serve"})
            names = [m.get("name") or m.get("model") for m in r.json().get("models", [])]
            picked = model or (names[0] if names else "")
            return _record_test(db, "llm", {"ok": True, "message": "Ollama connected",
                                             "detail": "Ollama " + str(len(names)) + " models; " + (picked or "none selected") + ". api/tags in " + str(latency) + " ms.",
                                             "latency_ms": latency})
        if prov.id == "anthropic":
            t0 = time.perf_counter()
            r = httpx.post(base + "/messages",
                           headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                    "Content-Type": "application/json"},
                           json={"model": model or "claude-3-haiku-20240307", "max_tokens": 8,
                                 "messages": [{"role": "user", "content": "hi"}]},
                           timeout=TEST_TIMEOUT)
            latency = int((time.perf_counter() - t0) * 1000)
            if r.status_code in (200, 201):
                return _record_test(db, "llm", {"ok": True, "message": "Anthropic connected",
                                                 "detail": "API key accepted; /messages in " + str(latency) + " ms.",
                                                 "latency_ms": latency})
            if r.status_code in (401, 403):
                return _record_test(db, "llm", {"ok": False, "message": "Anthropic rejected the API key",
                                                 "fix_hint": "x-api-key is invalid or revoked."})
            return _record_test(db, "llm", {"ok": False, "message": "Anthropic error (HTTP " + str(r.status_code) + ")",
                                             "detail": r.text[:120], "fix_hint": "Check the model name and that the endpoint is reachable."})
        # OpenAI-compatible providers: list /models = cheap token check.
        t0 = time.perf_counter()
        r = httpx.get(base + "/models", headers=_llm_headers(key, eff["headers"]), timeout=TEST_TIMEOUT)
        latency = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            data = r.json().get("data") or []
            ids = [m.get("id") or m.get("name") for m in data][:4]
            return _record_test(db, "llm", {"ok": True, "message": prov.label + " connected",
                                             "detail": "Key accepted; " + str(len(data)) + " models" + (" (" + ", ".join(x for x in ids if x) + ")" if ids else "") + ". /models in " + str(latency) + " ms.",
                                             "latency_ms": latency})
        if r.status_code in (401, 403):
            return _record_test(db, "llm", {"ok": False, "message": prov.label + " rejected the API key",
                                             "fix_hint": "Enter a valid " + prov.label + " API key."})
        return _record_test(db, "llm", {"ok": False, "message": prov.label + " error (HTTP " + str(r.status_code) + ")",
                                         "detail": r.text[:120], "fix_hint": "Check the Base URL and key."})
    except Exception as exc:
        if prov.id == "ollama":
            return _record_test(db, "llm", {"ok": False,
                                             "message": "Ollama not running at " + (base or "http://localhost:11434"),
                                             "detail": "Could not reach GET " + (base or "http://localhost:11434") + "/api/tags (" + str(exc) + ")",
                                             "fix_hint": "start it with: ollama serve"})
        return _record_test(db, "llm", {"ok": False, "message": prov.label + " not reachable at " + (base or "the configured Base URL"),
                                         "detail": str(exc),
                                         "fix_hint": "Check the Base URL and that " + prov.label + " is reachable (firewall, network)."})


def test_integration(db, integ_id, values=None):
    """Real connection test. `values` are transient form overrides (optional)
    so the user can test BEFORE saving; the result is stored with a timestamp."""
    integ = CATALOG.get(integ_id)
    if integ is None:
        return {"ok": False, "message": "unknown integration"}
    eff = _effective(db, integ, values)
    prov = eff["prov"]
    if prov is None:
        return _record_test(db, integ_id, {"ok": False, "message": "no provider configured"})
    if not cfg(db, integ).get("enabled", True):
        return _record_test(db, integ_id, {"ok": False, "message": "Integration is disabled"})

    # Explicit demo/mock/local sinks only ever report success as themselves.
    if prov.id == "mock":
        return _record_test(db, integ_id, {"ok": True, "message": prov.label + " ready",
                                            "detail": "Mock, no real service - canned/demo output only."})
    if prov.id == "file":
        return _record_test(db, integ_id, {"ok": True, "message": "File sink ready",
                                            "detail": "Dry-run outbox - writes .eml files. No real SMTP."})
    if prov.id == "local":
        return _record_test(db, integ_id, {"ok": True, "message": "Local file hosting ready",
                                            "detail": "Writes demo sites to backend/data/demo_sites."})
    if prov.id == "none":
        return _record_test(db, integ_id, {"ok": False, "message": "No DNC provider - voice stays fail-closed",
                                            "fix_hint": "Configure a DNC provider to enable voice calls."})
    if prov.id == "identity":
        return _record_test(db, integ_id, {"ok": True, "message": "Sender identity is set",
                                            "detail": "Identity fields saved."})

    if not has_required_fields(db, integ) and not _transient_ok(db, integ, eff, prov):
        missing = missing_fields(db, integ)
        return _record_test(db, integ_id, {"ok": False, "message": "Not configured",
                                            "detail": "Missing: " + (", ".join(missing) or "configuration"),
                                            "fix_hint": "Enter the required fields, or test with current form values."})

    if integ_id == "llm":
        return _test_llm(db, eff)
    if integ_id == "places":
        return _test_places(db, eff, prov)
    if integ_id == "osm":
        base = eff["base"] or prov.base_url_default or settings.overpass_base_url
        url = base.rstrip("/")
        if not url.endswith("/interpreter") and "/api/interpreter" not in url:
            url = url + "/api/interpreter"
        return _probe(db, integ_id, url, "Overpass endpoint reachable", "Overpass unreachable")
    if integ_id == "hosting":
        return _test_hosting(db, eff, prov)
    if integ_id == "email":
        return _test_email(db, eff, prov)
    if integ_id == "voice":
        return _test_voice(db, eff, prov)
    if integ_id == "dnc":
        return _test_dnc(db, eff, prov)
    if integ_id == "apify":
        from app.core.apify import validate_token
        return validate_token(db, eff["key"])
    return _record_test(db, integ_id, {"ok": True, "message": "Connection OK"})


def _transient_ok(db, integ, eff, prov):
    """True when unsaved form values satisfy the required fields."""
    if prov.id in ("none", "mock", "local", "file", "identity"):
        return True
    if prov.needs_key and eff["key"]:
        return True
    if prov.base_url_editable and eff["base"]:
        return True
    if integ.id == "email" and prov.id == "smtp" and eff["smtp"]["host"]:
        return True
    return False

def _test_places(db, eff, prov):
    key = eff["key"]
    if not key:
        return _record_test(db, "places", {"ok": False, "message": "No Places API key",
                                            "fix_hint": "Enter a Google Places API key."})
    try:
        t0 = time.perf_counter()
        r = httpx.get("https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
                      params={"input": "Singapore", "inputtype": "textquery",
                              "fields": "name,geometry", "key": key}, timeout=TEST_TIMEOUT)
        latency = int((time.perf_counter() - t0) * 1000)
        body = r.json()
        status = body.get("status")
        if status == "OK":
            cands = body.get("candidates") or []
            first = cands[0].get("name") if cands else None
            label = (" (e.g. " + first + ")") if first else ""
            return _record_test(db, "places", {"ok": True, "message": "Google Places connected",
                                                "detail": "Key accepted; query returned " + str(len(cands)) + " result(s)" + label + " in " + str(latency) + " ms.",
                                                "latency_ms": latency})
        if status == "REQUEST_DENIED":
            return _record_test(db, "places", {"ok": False, "message": "Google Places rejected the key (REQUEST_DENIED)",
                                                "fix_hint": "Key invalid or not enabled for Places API."})
        return _record_test(db, "places", {"ok": False, "message": "Places API error: " + str(status),
                                            "fix_hint": "Check the key and that Places API is enabled."})
    except Exception as exc:
        return _record_test(db, "places", {"ok": False, "message": "Places API unreachable: " + str(exc),
                                            "fix_hint": "Check network access to google."})
def _test_hosting(db, eff, prov):
    key = eff["key"]
    if not key:
        return _record_test(db, "hosting", {"ok": False, "message": "No " + prov.label + " token",
                                            "fix_hint": "Enter the token first."})
    base = eff["base"] or prov.base_url_default
    try:
        if (prov.id == "cloudflare_pages"):
            r = httpx.get(base.rstrip("/") + "/user/tokens/verify",
                          headers={"Authorization": "Bearer " + key}, timeout=TEST_TIMEOUT)
            ok = r.status_code == 200 and (r.json().get("result") or {}).get("status") == "active"
            return _record_test(db, "hosting", {"ok": ok,
                                                 "message": "Cloudflare token valid" if ok else "Cloudflare rejected token",
                                                 "fix_hint": "" if ok else "Token invalid or lacks Pages edit scope."})
        if prov.id == "netlify":
            r = httpx.get(base.rstrip("/") + "/user",
                          headers={"Authorization": "Bearer " + key}, timeout=TEST_TIMEOUT)
            ok = r.status_code == 200
            return _record_test(db, "hosting", {"ok": ok,
                                                 "message": "Netlify token valid" if ok else "Netlify rejected token",
                                                 "fix_hint": "" if ok else "Token invalid or missing sites scope."})
        return _record_test(db, "hosting", {"ok": False, "message": "Unknown hosting provider"})
    except Exception as exc:
        return _record_test(db, "hosting", {"ok": False, "message": "Error: " + str(exc),
                                             "fix_hint": "Is the hosting API reachable?"})
def _test_email(db, eff, prov):
    if prov.id == "smtp":
        return _test_smtp(db, eff)
    key = eff["key"]
    if not key:
        return _record_test(db, "email", {"ok": False, "message": "No " + prov.label + " API key",
                                            "fix_hint": "Enter the key first."})
    try:
        t0 = time.perf_counter()
        if prov.id == "brevo":
            r = httpx.get("https://api.brevo.com/v3/account", headers={"api-key": key}, timeout=TEST_TIMEOUT)
            ok = r.status_code == 200
            return _record_test(db, "email", {"ok": ok, "message": "Brevo key valid" if ok else "Brevo rejected key",
                                               "detail": "Account API in " + str(int((time.perf_counter() - t0) * 1000)) + " ms." if ok else "",
                                               "fix_hint": "" if ok else "Key invalid or lacks mail-send scope."})
        if prov.id == "resend":
            r = httpx.get("https://api.resend.com/domains", headers={"Authorization": "Bearer " + key}, timeout=TEST_TIMEOUT)
            ok = r.status_code == 200
            return _record_test(db, "email", {"ok": ok, "message": "Resend key valid" if ok else "Resend rejected key",
                                               "detail": "Domains endpoint in " + str(int((time.perf_counter() - t0) * 1000)) + " ms." if ok else "",
                                               "fix_hint": "" if ok else "Key invalid."})
        return _record_test(db, "email", {"ok": False, "message": "Unknown email provider"})
    except Exception as exc:
        return _record_test(db, "email", {"ok": False, "message": "Error: " + str(exc),
                                           "fix_hint": "Is the provider API reachable?"})
def _test_smtp(db, eff):
    smtp = eff["smtp"]
    host = smtp["host"]
    if not host:
        return _record_test(db, "email", {"ok": False, "message": "SMTP host missing",
                                            "fix_hint": "Enter SMTP host/port in the drawer."})
    import smtplib
    t0 = time.perf_counter()
    conn = None
    try:
        conn = smtplib.SMTP(host, int(smtp["port"] or 587), timeout=TEST_TIMEOUT)
        conn.ehlo()
        if conn.has_extn("starttls"):
            conn.starttls()
            conn.ehlo()
        if smtp["pass"]:
            conn.login(smtp["user"], smtp["pass"])
        latency = int((time.perf_counter() - t0) * 1000)
        return _record_test(db, "email", {"ok": True, "message": "SMTP login succeeded",
                                            "detail": host + ":" + str(smtp["port"]) + " authenticated" + (" as " + smtp["user"] if smtp["user"] else "") + " in " + str(latency) + " ms.",
                                            "latency_ms": latency})
    except smtplib.SMTPAuthenticationError:
        return _record_test(db, "email", {"ok": False, "message": "SMTP login failed - wrong credentials",
                                            "fix_hint": "Check SMTP username/password with your provider."})
    except Exception as exc:
        return _record_test(db, "email", {"ok": False, "message": "SMTP connection failed: " + str(exc),
                                            "fix_hint": "Check host, port and TLS settings."})
    finally:
        if conn is not None:
            try: conn.quit()
            except Exception: pass
def _test_voice(db, eff, prov):
    key = eff["key"]
    if not key:
        return _record_test(db, "voice", {"ok": False, "message": "No " + prov.label + " API key",
                                            "fix_hint": "Enter the key first."})
    base = eff["base"] or prov.base_url_default
    try:
        t0 = time.perf_counter()
        r = httpx.get(base.rstrip("/") + "/", headers={"Authorization": "Bearer " + key}, timeout=TEST_TIMEOUT)
        latency = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            return _record_test(db, "voice", {"ok": True, "message": prov.label + " connected",
                                               "detail": "API key accepted in " + str(latency) + " ms.", "latency_ms": latency})
        if r.status_code in (401, 403):
            return _record_test(db, "voice", {"ok": False, "message": prov.label + " rejected the API key",
                                               "fix_hint": "Key invalid or revoked for " + prov.label + "."})
        return _record_test(db, "voice", {"ok": False, "message": prov.label + " error (HTTP " + str(r.status_code) + ")",
                                           "fix_hint": "Check key and base URL."})
    except Exception as exc:
        return _record_test(db, "voice", {"ok": False, "message": "Error: " + str(exc),
                                           "fix_hint": "Is " + (base or "the voice API") + " reachable?"})
def _test_dnc(db, eff, prov):
    key = eff["key"]
    if not key:
        return _record_test(db, "dnc", {"ok": False, "message": "DNC registry key missing",
                                          "fix_hint": "Set the DNC registry API key."})
    base = eff["base"] or prov.base_url_default
    try:
        t0 = time.perf_counter()
        r = httpx.get(base.rstrip("/") + "/health", headers={"Authorization": "Bearer " + key}, timeout=TEST_TIMEOUT)
        latency = int((time.perf_counter() - t0) * 1000)
        if r.status_code in (200, 204):
            return _record_test(db, "dnc", {"ok": True, "message": "DNC registry reachable",
                                             "detail": "Health check in " + str(latency) + " ms.", "latency_ms": latency})
        if r.status_code in (401, 403):
            return _record_test(db, "dnc", {"ok": False, "message": "DNC registry rejected the key",
                                             "fix_hint": "Key invalid or lacks permission."})
        return _record_test(db, "dnc", {"ok": False, "message": "DNC registry error (HTTP " + str(r.status_code) + ")",
                                         "fix_hint": "Check the Base URL and key."})
    except Exception as exc:
        return _record_test(db, "dnc", {"ok": False, "message": "Error: " + str(exc),
                                         "fix_hint": "Is the DNC registry reachable?"})



def llm_model_list(db: Session, provider: str, base_url: str | None = None, api_key: str | None = None) -> list[str]:
    """Fetch the provider model list (empty means unable to fetch)."""
    prov = next((p for p in LLM_PROVIDERS if p.id == provider), None)
    if prov is None or prov.id == "mock":
        return []
    base = (base_url or prov.base_url_default or "").rstrip("/")
    if not base:
        return []
    try:
        if prov.id == "ollama":
            resp = httpx.get(base + "/api/tags", timeout=TEST_TIMEOUT)
            resp.raise_for_status()
            return [m.get("name") or m.get("model") for m in resp.json().get("models", [])]
        key = api_key or get_secret(db, prov.key_secret_key)
        headers = {"Authorization": "Bearer " + key} if key else {}
        resp = httpx.get(base + "/models", headers=headers, timeout=TEST_TIMEOUT)
        resp.raise_for_status()
        return [m.get("id") or m.get("name") for m in resp.json().get("data", [])]
    except Exception:
        return []


def health_summary(db: Session) -> dict:
    """X of Y required integrations working + checklist of what is still needed."""
    rows = []
    working = 0
    for iid in REQUIRED_IDS:
        integ = CATALOG[iid]
        st = status(db, integ)
        rows.append({
            "id": iid, "name": integ.name, "required": True,
            "state": st["state"], "label": st["label"], "detail": st["detail"],
            "ok": st["state"] in ("connected",) or (st["state"] == "configured" and integ.id == "identity"),
        })
        if rows[-1]["ok"]:
            working += 1
    required = len(REQUIRED_IDS)
    return {
        "working": working,
        "required": required,
        "ok": working == required,
        "message": f"{working} of {required} required integrations working",
        "checklist": rows,
    }