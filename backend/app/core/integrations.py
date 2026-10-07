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
    ProviderDef("mock", "Mock (dry-run)", note="Returns a canned transcript. Default."),
    ProviderDef("vapi", "Vapi", needs_key=True, key_secret_key="voice.vapi.api_key"),
    ProviderDef("retell", "Retell", needs_key=True, key_secret_key="voice.retell.api_key"),
    ProviderDef("bland", "Bland AI", needs_key=True, key_secret_key="voice.bland.api_key"),
    ProviderDef("custom", "Custom (OpenAI-compatible)", needs_key=True, key_secret_key="voice.custom.api_key",
                base_url_default="", base_url_editable=True),
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
    result["at"] = _now()
    set_setting(db, f"integration.{integ_id}.last_test", result)
    # refresh last_verified on the secret too (if an api key was used)
    prov = provider_for(db, CATALOG[integ_id])
    if prov is not None and prov.needs_key:
        try:
            mod = CATALOG[integ_id]
            row = db.query(__import__("app.models.integration_secret", fromlist=["IntegrationSecret"]).IntegrationSecret).filter(
                __import__("app.models.integration_secret", fromlist=["IntegrationSecret"]).IntegrationSecret.key == prov.key_secret_key).first()
            if row is not None:
                row.last_verified_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:  # noqa: BLE001
            pass
    return result



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


def _openai_chat_test(db, base, key, model) -> dict:
    if not key:
        return _record_test(db, "llm", {"ok": False, "message": "No API key configured",
                                         "fix_hint": "Enter the provider API key in Configure."})
    if not model:
        return _record_test(db, "llm", {"ok": False, "message": "Model not set",
                                         "fix_hint": "Pick a model or type a custom model name."})
    t0 = time.perf_counter()
    try:
        r = httpx.post(base.rstrip('/') + "/chat/completions",
                       headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
                       json={"model": model, "messages": [{"role": "user", "content": "Reply with OK."}],
                             "max_tokens": 5}, timeout=30)
        latency = int((time.perf_counter() - t0) * 1000)
        if r.status_code == 200:
            answered = (((r.json().get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            return _record_test(db, "llm", {"ok": True, "message": "LLM connected",
                                             "detail": f"Model {model} answered in {latency} ms: '{answered[:20]}'",
                                             "latency_ms": latency})
        return _record_test(db, "llm", {"ok": False, "message": f"Provider returned HTTP {r.status_code}: {r.text[:120]}",
                                         "fix_hint": "Check the API key and model name."})
    except Exception as exc:
        return _record_test(db, "llm", {"ok": False, "message": "Request failed: " + str(exc),
                                         "fix_hint": "Check the Base URL and that the endpoint is reachable."})


def test_integration(db: Session, integ_id: str) -> dict:
    import httpx as _httpx  # noqa
    integ = CATALOG.get(integ_id)
    if integ is None:
        return {"ok": False, "message": "unknown integration"}
    prov = provider_for(db, integ)
    if prov is None:
        return _record_test(db, integ_id, {"ok": False, "message": "no provider configured"})

    if not cfg(db, integ).get("enabled", True):
        return _record_test(db, integ_id, {"ok": False, "message": "Integration is disabled"})

    if prov.id in ("mock", "file", "local", "identity"):
        return _record_test(db, integ_id, {"ok": True, "message": prov.label + " is always available",
                                            "detail": prov.label + " — no network needed."})
    if prov.id == "none":
        return _record_test(db, integ_id, {"ok": False, "message": "No DNC provider — voice stays fail-closed",
                                            "fix_hint": "Configure a DNC provider to enable voice calls."})

    if integ_id == "identity":
        return _record_test(db, integ_id, {"ok": True, "message": "Sender identity is set",
                                            "detail": "Identity fields saved."})
    if integ_id == "llm":
        return _test_llm(db, prov)
    if integ_id == "places":
        if not _is_key_set(db, prov.key_secret_key):
            return _record_test(db, integ_id, {"ok": False, "message": "No Places API key configured",
                                                "fix_hint": "Set a Google Places API key (free tier)."})
        return _record_test(db, integ_id, {"ok": True, "message": "Google Places configured",
                                            "detail": "Credential present — a live query runs during discovery."})
    if integ_id == "osm":
        base = cfg(db, integ).get("base_url") or prov.base_url_default or settings.overpass_base_url
        url = base.rstrip('/')
        if not url.endswith("/interpreter") and "/api/interpreter" not in url:
            url = url + "/api/interpreter"
        return _probe(db, integ_id, url, "Overpass endpoint reachable", "Overpass unreachable")
    if integ_id == "hosting":
        if prov.id == "local":
            return _record_test(db, integ_id, {"ok": True, "message": "Local file hosting always available"})
        if not _is_key_set(db, prov.key_secret_key):
            return _record_test(db, integ_id, {"ok": False, "message": "No hosting token configured",
                                                "fix_hint": "Enter a " + prov.label + " API token."})
        base = cfg(db, integ).get("base_url") or prov.base_url_default
        key = get_secret(db, prov.key_secret_key) or ""
        try:
            if prov.id == "cloudflare_pages":
                r = httpx.get(base.rstrip('/') + "/user/tokens/verify",
                              headers={"Authorization": "Bearer " + key}, timeout=15)
                ok = r.status_code == 200
                return _record_test(db, integ_id, {"ok": ok,
                                                    "message": "Cloudflare token valid" if ok else f"Cloudflare rejected token (HTTP {r.status_code})",
                                                    "fix_hint": "" if ok else "Check the token has Pages edit scope."})
            if prov.id == "netlify":
                r = httpx.get(base.rstrip('/') + "/user",
                              headers={"Authorization": "Bearer " + key}, timeout=15)
                ok = r.status_code == 200
                return _record_test(db, integ_id, {"ok": ok,
                                                    "message": "Netlify token valid" if ok else f"Netlify rejected token (HTTP {r.status_code})",
                                                    "fix_hint": "" if ok else "Check the token and site membership."})
        except Exception as exc:
            return _record_test(db, integ_id, {"ok": False, "message": "Error: " + str(exc),
                                                "fix_hint": "Is the hosting API reachable?"})
    if integ_id == "email":
        if prov.id == "file":
            return _record_test(db, integ_id, {"ok": True, "message": "File sender always available",
                                                "detail": "Dry-run outbox — writes .eml files."})
        host = cfg(db, integ).get("smtp_host") or ""
        if prov.id == "smtp":
            if not host:
                return _record_test(db, integ_id, {"ok": False, "message": "SMTP host missing",
                                                    "fix_hint": "Set SMTP host/port in the Configure drawer."})
            has_secret = (_is_key_set(db, "email.smtp.password") or False)
            return _record_test(db, integ_id, {"ok": True, "message": "SMTP configured",
                                                "detail": f"SMTP {host} — credentials {'present' if has_secret else 'optional (open relay)'}"})
        if prov.id in ("brevo", "resend"):
            if not _is_key_set(db, prov.key_secret_key):
                return _record_test(db, integ_id, {"ok": False, "message": "No " + prov.label + " API key",
                                                    "fix_hint": "Enter the " + prov.label + " API key."})
            return _record_test(db, integ_id, {"ok": True, "message": prov.label + " configured",
                                                "detail": prov.label + " key present — dry-run sends stop before SMTP."})
    if integ_id == "voice":
        if not _is_key_set(db, prov.key_secret_key):
            return _record_test(db, integ_id, {"ok": False, "message": "No " + prov.label + " API key",
                                                "fix_hint": "Set the voice API key."})
        return _record_test(db, integ_id, {"ok": True, "message": prov.label + " configured",
                                            "detail": "Voice stays in dry-run — first live call is compliance-gated."})
    if integ_id == "dnc":
        if not _is_key_set(db, prov.key_secret_key):
            return _record_test(db, integ_id, {"ok": False, "message": "DNC registry key missing",
                                                "fix_hint": "Set the DNC registry API key."})
        return _record_test(db, integ_id, {"ok": True, "message": "DNC provider configured"})
    if integ_id == "apify":
        from app.core.apify import validate_token
        return validate_token(db, get_secret(db, prov.key_secret_key) or "")
    return _record_test(db, integ_id, {"ok": True, "message": "Connection OK"})


def _test_llm(db: Session, prov: ProviderDef) -> dict:
    integ = CATALOG["llm"]
    c = cfg(db, integ)
    base = c.get("base_url") or prov.base_url_default
    key = get_secret(db, prov.key_secret_key) if prov.needs_key else None
    model = c.get("model") or (prov.static_models[0] if prov.static_models else "")

    if prov.id == "ollama":
        t0 = time.perf_counter()
        try:
            r = httpx.get(base.rstrip('/') + "/api/tags", timeout=30)
            latency = int((time.perf_counter() - t0) * 1000)
            if r.status_code != 200:
                return _record_test(db, "llm", {"ok": False, "message": f"Ollama unreachable (HTTP {r.status_code})",
                                                 "fix_hint": "Start Ollama (ollama serve) and set the Base URL."})
            names = [m.get("name") or m.get("model") for m in r.json().get("models", [])]
            model = model or (names[0] if names else "")
            return _record_test(db, "llm", {"ok": True, "message": "Ollama connected",
                                             "detail": f"Ollama — {len(names)} models; {model or 'no model'} ready.",
                                             "latency_ms": latency})
        except Exception as exc:
            return _record_test(db, "llm", {"ok": False, "message": "Ollama unreachable: " + str(exc),
                                             "fix_hint": "Start Ollama and confirm the Base URL (default http://localhost:11434)."})
    return _openai_chat_test(db, base, key, model)


def llm_model_list(db: Session, provider: str, base_url: str | None = None, api_key: str | None = None) -> list[str]:
    """Fetch the provider's model list (empty means 'unable to fetch')."""
    prov = next((p for p in LLM_PROVIDERS if p.id == provider), None)
    if prov is None:
        return []
    base = (base_url or prov.base_url_default or "").rstrip('/')
    if not base:
        return []
    try:
        if prov.id == "ollama":
            resp = httpx.get(base + "/api/tags", timeout=20)
            resp.raise_for_status()
            return [m.get("name") or m.get("model") for m in resp.json().get("models", [])]
        key = api_key or get_secret(db, prov.key_secret_key)
        headers = {"Authorization": "Bearer " + key} if key else {}
        resp = httpx.get(base + "/models", headers=headers, timeout=20)
        resp.raise_for_status()
        return [m.get("id") or m.get("name") for m in resp.json().get("data", [])]
    except Exception:  # noqa: BLE001
        return []


def health_summary(db: Session) -> dict:
    """X of Y required integrations working + checklist of what's still needed."""
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
