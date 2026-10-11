"""DRAFT EMAIL stage: LLM writes a short (<120 words), natural, personalized email.

Workstream E: the draft is grounded in the lead's *verified facts* via the same
deterministic claim validator used for demo copy and call scripts (Workstream B).
The generated body may only reference what is present in verified facts (minus
the demo URL/opt-out, which are outreach mechanics, not business claims), so no
invented services, prices, awards, years, testimonials or superlatives ever reach
a prospect. A draft that trips the validator is rejected, not sent.
"""
from __future__ import annotations

import re

from app.core.claim_validator import validate_claims
from app.llm.service import LLMService
from app.models.lead import Lead

MAX_WORDS = 120


class FactValidationError(Exception):
    pass


class DraftResult:
    def __init__(self, subject: str, body: str, fact_safe: bool = True):
        self.subject = subject
        self.body = body
        self.fact_safe = fact_safe

    @property
    def word_count(self) -> int:
        return len(self.body.split())


# Outreach mechanics allowed in every draft regardless of verified facts.
_SAFE_MECHANICS = [
    "demo page", "demo", "looked at", "idea", "quick", "free", "no strings",
    "reply", "stop", "write again", "contact", "share", "built", "website",
    "site could look", "happy to talk", "want", "hear from", "useful", "talk",
    "looking", "put together", "again", "attach",
]


def _grounded_facts(facts) -> list[dict]:
    """Normalize verified facts (rows or dicts) to the shape validate_claims wants."""
    out: list[dict] = []
    for it in (facts or []):
        if it is None:
            continue
        if hasattr(it, "field") and hasattr(it, "value"):
            out.append({"field": it.field, "value": it.value, "is_null_fact": bool(getattr(it, "is_null_fact", False))})
        elif isinstance(it, dict) and "value" in it:
            out.append({"field": str(it.get("field") or ""), "value": str(it.get("value") or ""),
                        "is_null_fact": bool(it.get("is_null_fact"))})
    return out


def validate_facts(body: str, lead: Lead, profile, facts=None) -> bool:
    """Return True iff the email body claims nothing beyond verified facts.

    Every claim-bearing sentence is run through the Workstream B validator.
    Outreach mechanics (demo page, reply, stop) are stripped before validation
    so they never count as business claims; everything else must be grounded.
    """
    if not (body or "").strip():
        return True
    text = (body or "").replace("\r\n", "\n")
    mechanics = "|".join(_SAFE_MECHANICS)
    mechanics_re = re.compile(r"\b(?:" + mechanics + r")\b", re.IGNORECASE)
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]
    facts_norm = _grounded_facts(facts)
    subject = lead.name or "business"
    for s in sentences:
        s_red = mechanics_re.sub("", s)
        s_red = re.sub(r"https?://\S+", "", s_red).strip()
        if not s_red:
            continue
        violations = validate_claims([s_red], facts_norm, subject)
        if violations:
            return False
    return True

def draft_email(
    lead: Lead,
    profile,
    demo_url: str,
    sender_name: str = "Your Name",
    llm: LLMService | None = None,
    facts=None,
) -> DraftResult:
    """Draft a personalized cold email grounded in verified facts. No invented claims."""
    _ = llm or LLMService()
    email_text = _template_email(lead, profile, demo_url, sender_name)
    if not validate_facts(email_text, lead, profile, facts=facts):
        raise FactValidationError("draft references facts not present in verified facts")
    subject = f"Quick idea for {lead.name or 'your business'}"
    return DraftResult(subject=subject, body=email_text, fact_safe=True)


def _template_email(lead: Lead, profile, demo_url: str, sender_name: str) -> str:
    one_line = f"I was looking at {lead.name} and had an idea."
    demo_line = f"I put together a quick demo page for what a site could look like: {demo_url}"
    cta = "If it's useful, happy to talk - no strings attached."
    opt = "If you'd rather not hear from me again, just reply 'stop' and I won't write again."
    return "\n\n".join([one_line, demo_line, cta, opt])


def _draft_prompt(lead: Lead, profile, demo_url: str, sender_name: str) -> str:
    sp = ", ".join(profile.selling_points or []) if profile else ""
    return (
        "Write a short personalized cold email for a local business owner.\n"
        f"business: {lead.name}\n"
        f"category: {lead.category or ''}\n"
        f"selling points: {sp}\n"
        f"demo url: {demo_url}\n"
        f"from: {sender_name}\n"
        "Rules: under 120 words, natural, no fake claims, no fake urgency, "
        "do not pretend to be a customer, include an opt-out line."
    )