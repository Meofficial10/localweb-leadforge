"""Safe claim generation (Workstream B).

Wraps an LLM call that produces claims with a retry + fallback loop:

1. Build the prompt from verified facts ONLY (no unverified copy is leaked in).
2. Call the LLM; expect JSON with tagged claims: each claim entry has
   {text, kind: 'verified'|'generic', source_fact_id}: string|null}.
3. Validate claims deterministically (app.core.claim_validator).
   If violations are found, retry up to 2 times, each time listing the exact
   violations so the model can correct them.
4. If it still fails, fall back to a deterministic template built only from
   verified facts / generic phrasing — no unverified claims ever emitted.
"""
from __future__ import annotations

import json
from typing import Any

from app.core.claim_validator import (
    GENERIC_PHRASES,
    validate_claims,
    verified_values,
)
from app.llm.base import LLMSchemaError

MAX_RETRIES = 2


def _fact_index(facts: list[dict]) -> dict[str, str]:
    idx: dict[str, str] = {}
    for it in (facts or []):
        fid = it.get("id")
        if fid:
            idx[str(fid)] = str(it.get("value") or "")
    return idx


def validate_tagged_claims(entries: list[dict], facts: list[dict], subject: str,
                           fact_index: dict[str, str]) -> list[dict]:
    """Validate a list of tagged claim dicts. Returns violations.

    Entry shapes:
      {"text": "...", "kind": "verified", "source_fact_id": "<id>"}
      {"text": "...", "kind": "generic"}   # no source_fact_id required
    Rules:
      - verified: source_fact_id must exist AND text must appear in that fact value.
      - generic: text must be a neutral generic phrase (no specific claims).
    """
    violations: list[dict] = []
    for e in entries or []:
        if not isinstance(e, dict):
            continue
        text = str(e.get("text") or "").strip()
        if not text:
            continue
        kind = str(e.get("kind") or "generic")
        if kind == "verified":
            fid = str(e.get("source_fact_id") or "")
            if fid not in fact_index:
                violations.append({"claim": text, "reason": "verified kind but unknown source_fact_id"})
                continue
            val = fact_index[fid]
            from app.core.claim_validator import _norm
            if _norm(text) not in _norm(val):
                violations.append({"claim": text, "reason": f"verified text not in fact '{val}'"})
        else:
            # generic: must be from the neutral whitelist + pass claim validator
            from app.core.claim_validator import _norm
            if _norm(text) in _norm_collect(GENERIC_PHRASES):
                continue
            v = validate_claims([text], facts, subject)
            if v:
                violations.extend(v)
            else:
                violations.append({"claim": text, "reason": "generic claim not in neutral allowlist"})
    return violations


def _norm_collect(phrases) -> set[str]:
    from app.core.claim_validator import _norm
    return {_norm(x) for x in phrases}


def generate_safe_claims(
    llm,
    prompt: str,
    schema: dict,
    facts: list[dict],
    subject: str = "",
    retries: int = MAX_RETRIES,
    field: str = "claims",
    fallback: list[dict] | None = None,
) -> list[dict]:
    """Call llm.generate with retry-on-violation; return validated claim entries.
    Raises after exhausting retries; callers catch and use fallback."""
    fact_index = _fact_index(facts)
    attempt = 0
    last_err = None
    while attempt <= retries:
        try:
            data = llm.generate(prompt, schema)
        except Exception as exc:  # noqa: BLE001
            last_err = f"llm error: {exc}"
            attempt += 1
            continue
        entries = data.get(field) if isinstance(data, dict) else None
        if not isinstance(entries, list):
            last_err = "output missing field list"
            attempt += 1
            continue
        violations = validate_tagged_claims(entries, facts, subject, fact_index)
        if not violations:
            return entries
        last_err = "; ".join(f"{v['claim']!r} -> {v['reason']}" for v in violations[:5])
        if attempt < retries:
            prompt = _append_corrections(prompt, violations)
        attempt += 1
    raise ClaimValidationError(last_err or "claims failed validation")


class ClaimValidationError(Exception):
    pass


def _append_corrections(prompt: str, violations: list[dict]) -> str:
    note = "Previously rejected claims (do NOT repeat these; replace with verified facts or neutral generic phrasing): "
    note += "; ".join(f"{v['claim']!r} -> {v['reason']}" for v in violations[:8])
    return prompt + "\n\n" + note
