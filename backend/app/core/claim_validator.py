"""Deterministic claim validator (Workstream B).

Guarantees that generated copy (demo site, email, call script) never asserts a
fact that is not in the lead's *verified facts*. Verified facts are collected by
app.core.facts.collect_verified_facts; generated copy is written by the LLM and
then passed through validate_claims / assert_claim_safe before being stored.

What counts as an unverifiable claim (blocked unless present in verified facts):
- specific services ("We do implants", "Laser hair removal")
- prices / fees / costs
- years in business / "since <year>"
- awards / certifications / accreditations
- payment methods accepted
- equipment owned
- staff members / named personnel
- testimonials / reviews / rankings / patient counts
- guarantees / superlatives ("best in town", "#1")

Anything else (neutral category wording, generic CTAs) is allowed as kind='generic'.
"""
from __future__ import annotations

import re

# Each entry: (reason, compiled regex). If the pattern matches and the matched
# phrase is not grounded in a verified fact value, the claim is a violation.
CLAIM_FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("prices", re.compile(r"(?i)\b(?:price|pricing|fee|fees|cost|charges?)\b|\$\s?\d|\b\d+\s*(?:sgd|usd|rm)\b")),
    ("years_in_business", re.compile(r"(?i)\b(?:since\s+)?(?:19\d{2}|20\d{2})\b|\b\d+\s*(?:years|yrs)\s+(?:of\s+)?(?:experience|service|in business)\b")),
    ("awards", re.compile(r"(?i)\b(award|winner|accredited|certified|certification|best in|#1|ranked|top rated)\b")),
    ("payments", re.compile(r"(?i)\b(paynow|visa|mastercard|amex|nets|fpx|payment|invoice|reimburse)\b")),
    ("equipment", re.compile(r"(?i)\b(lasers?|mri\w*|ct scanners?|x-rays?|ultrasound|hydrojet|cnc machines?)\b")),
    ("staff", re.compile(r"(?i)(dr.|specialist|therapist|consultant|hnv|our team)|[A-Z][a-z]+s[A-Z][a-z]+")),
    ("testimonials", re.compile(r"(?i)\b(testimonial|review|rating|fame|popular|trusted by|recommended by)\b|\b\d+(\.[0-9])?\s*(out of 5)?\s*stars?\b")),
    ("patient_counts", re.compile(r"(?i)\b\d+\s*(patients|clients|customers|members|people)\b")),
    ("guarantees", re.compile(r"(?i)\b(guarantee|guaranteed|satisfaction guaranteed|no-risk|risk-free)\b")),
    ("superlatives", re.compile(r"(?i)\b(best|cheap(?:est)?|finest|leading|premier|premium|trusted|largest|first choice)\b")),
]

# Explicitly-permitted generic framing allowed when the fact is unknown. These are
# neutral category wordings that never assert a service/person/price/award.
GENERIC_PHRASES = {
    "book an appointment",
    "visit us",
    "visit us today",
    "walk-ins welcome",
    "call us today",
    "contact us",
    "get in touch",
    "learn more",
    "our opening hours",
    "convenient location",
    "serving the local area",
    "local and approachable",
}


def _norm(s: str) -> str:
    return re.sub(r"[\s]+", " ", (s or "").strip().lower())


def verified_values(facts: list[dict] | dict) -> list[str]:
    """Flatten verified facts into a list of searchable lower-case values."""
    values: list[str] = []
    if isinstance(facts, dict):
        items = []
        for field, v in facts.items():
            if isinstance(v, list):
                for x in v:
                    items.append({"field": field, "value": str(x), "source": "verified"})
            elif v is not None:
                items.append({"field": field, "value": str(v), "source": "verified"})
    else:
        items = facts or []
    for it in items:
        if isinstance(it, dict) and it.get("value") is not None:
            values.append(_norm(it["value"]))
    return [v for v in values if v]


def _grounded(phrase: str, fact_values: list[str], subject_name: str) -> bool:
    p = _norm(phrase)
    if not p:
        return True
    if p in GENERIC_PHRASES:
        return True
    for v in fact_values:
        # grounded if the phrase is contained in a verified value verbatim
        if v and (p in v or v in p):
            return True
    # the business name itself may appear (it's verified)
    n = _norm(subject_name or "")
    if n and (p == n or n in p):
        return True
    return False


def validate_claims(claims, facts, subject_name="") -> list[dict]:
    """Return a list of {claim, reason} violations for copy claims.

    claims: list[str] of generated copy (services, selling points, summary lines).
    facts:  list of VerifiedFact-like dicts, or dict {field: value(s)}.
    """
    values = verified_values(facts)
    violations: list[dict] = []
    for claim in claims or []:
        c = _norm(claim)
        if not c:
            continue
        for reason, pat in CLAIM_FORBIDDEN_PATTERNS:
            m = pat.search(claim)
            if not m:
                continue
            # allowed only if exactly grounded in a verified value
            phrase = m.group(0)
            if not _grounded(phrase, values, subject_name):
                if not any(_grounded(phrase, [v], subject_name) for v in values):
                    violations.append({"claim": claim, "reason": f"unverified {reason}: '{phrase}'"})
    return violations


def claim_is_safe(text: str, facts, subject_name="") -> bool:
    """Convenience: single-line copy check (summary lines, email body)."""
    lines = [ln.strip() for ln in re.split(r"[\n.!?]+", text) if ln.strip()]
    return not validate_claims(lines, facts, subject_name)
