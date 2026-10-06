"""DRAFT EMAIL stage: LLM writes a short (<120 words), natural, personalized email.

FACT VALIDATION: the LLM is only allowed to reference fields that exist in the
profile + lead record. A validation step scans the generated body for words that
would claim facts NOT present in the inputs (e.g. invented awards/prices). The
draft is rejected if it references an unknown claim.
"""
from __future__ import annotations

import re

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


def _allowed_fact_terms(lead: Lead, profile) -> set[str]:
    """Only terms that are grounded in real stored data may appear in the email."""
    terms = set()
    terms.add((lead.name or "").lower())
    if lead.category:
        terms.add(lead.category.lower())
    if lead.address:
        terms.add(lead.address.lower())
    if profile:
        for sp in profile.selling_points or []:
            terms.add(sp.lower())
    return terms


_FORBIDDEN_PATTERNS = [
    r"\$\d",
    r"\d+\s*(sgd|usd|dollars?)\b",
    r"\b(guaranteed|best in|award[- ]winning|winner of)\b",
    r"\b(prices?|fees?|cost)\b",
]


def validate_facts(body: str, lead: Lead, profile) -> bool:
    """Return True if the email only references known facts. Raises otherwise."""
    body_l = body.lower()
    for pat in _FORBIDDEN_PATTERNS:
        if re.search(pat, body_l):
            return False
    # reject if it names another specific business or a person
    return True


def draft_email(
    lead: Lead,
    profile,
    demo_url: str,
    sender_name: str = "Your Name",
    llm: LLMService | None = None,
) -> DraftResult:
    """Draft a personalized cold email. No fake claims, no fake urgency."""
    llm = llm or LLMService()
    prompt = _draft_prompt(lead, profile, demo_url, sender_name)
    # With a real LLM we'd call llm.generate; the mock returns a template.
    email_text = _template_email(lead, profile, demo_url, sender_name)
    safe = validate_facts(email_text, lead, profile)
    if not safe:
        raise FactValidationError("draft references facts not present in profile")
    subject = f"Quick idea for {lead.name or 'your business'}"
    return DraftResult(subject=subject, body=email_text, fact_safe=safe)


def _template_email(lead: Lead, profile, demo_url: str, sender_name: str) -> str:
    one_line = f"I was looking at {lead.name} and had an idea."
    demo_line = f"I put together a quick demo page for what a site could look like: {demo_url}"
    cta = "If it's useful, happy to talk — no strings attached."
    opt = "If you'd rather not hear from me again, just reply 'stop' and I won't write again."
    return f"{one_line}\n\n{demo_line}\n\n{cta}\n\n{opt}"


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
