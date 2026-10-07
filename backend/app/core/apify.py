"""Apify integration: run Google-Maps scraper actor, poll the run, fetch dataset items.

This module is the adapter behind the 'Apify' lead source. M3 fills in the full
actor-run flow (start -> poll with backoff -> fetch dataset -> normalize). The
token-validation helper is already wired into the integrations test-connection so
the M2 integrations page can validate the API token.
"""
from __future__ import annotations

import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException as _http

APIFY_API = "https://api.apify.com/v2"


def _token(db: Session) -> str | None:
    from app.core.crypto import get_secret
    return get_secret(db, "apify.api_token")


def validate_token(db: Session, token: str | None = None) -> dict:
    """Check the Apify API token is valid (GET /v2/users/me)."""
    from app.core.integrations import _record_test
    tok = token or _token(db)
    if not tok:
        return _record_test(db, "apify", {"ok": False, "message": "No Apify token configured",
                                           "fix_hint": "Enter an Apify API token (Settings -> Integrations in Apify)."})
    try:
        r = httpx.get(APIFY_API + "/users/me", params={"token": tok}, timeout=30)
        if r.status_code == 200:
            username = (r.json().get("data") or {}).get("username", "account")
            return _record_test(db, "apify", {"ok": True, "message": "Apify token valid",
                                               "detail": f"Authenticated as @{username} — actor runs enabled.",
                                               "actor_id": None})
        if r.status_code in (401, 403):
            return _record_test(db, "apify", {"ok": False, "message": "Apify rejected the token (HTTP " + str(r.status_code) + ")",
                                               "fix_hint": "The token is invalid or revoked — get a new one from apify.com."})
        if r.status_code == 429:
            return _record_test(db, "apify", {"ok": False, "message": "Apify rate limit (HTTP 429)",
                                               "fix_hint": "Reduce actor run frequency or raise the budget cap."})
        return _record_test(db, "apify", {"ok": False, "message": "Apify error (HTTP " + str(r.status_code) + ")",
                                           "fix_hint": "Check the actor and network."})
    except Exception as exc:
        return _record_test(db, "apify", {"ok": False, "message": "Apify unreachable: " + str(exc),
                                           "fix_hint": "Is api.apify.com reachable?"})
