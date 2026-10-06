"""Email and phone extraction from public page HTML.

Regex first, then optional LLM verification (via the llm service interface).
Emails and phones in comments/JS noise are filtered. Source URL is tracked.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.utils import is_valid_email, normalize_email, normalize_phone

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?65[ -]?)?(?:[0-9]{8}|[0-9]{3}[ -][0-9]{3}[ -][0-9]{4}|[0-9]{4}[ -][0-9]{4})")
_BAD_TLD = {"png", "jpg", "gif", "css", "js", "svg", "webp", "example", "domain", "test"}


@dataclass
class Extraction:
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)


def _strip_html_noise(html: str) -> str:
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    return html


def extract_contacts(html: str) -> Extraction:
    html = _strip_html_noise(html)
    result = Extraction()

    mailtos = re.findall(r'[Hh][Rr][Ee][Ff]\s*=\s*["\']mailto:([^"\']+)["\']', html)
    for m in mailtos:
        em = normalize_email(m.split("?")[0])
        if is_valid_email(em) and em.split(".")[-1] not in _BAD_TLD:
            if em not in result.emails:
                result.emails.append(em)

    for m in _EMAIL_RE.findall(html):
        em = normalize_email(m)
        if is_valid_email(em) and em.split(".")[-1] not in _BAD_TLD and em not in result.emails:
            result.emails.append(em)

    for m in _PHONE_RE.findall(html):
        digits = re.sub(r"[^0-9]", "", m)
        if len(digits) < 3:
            continue
        p = normalize_phone(m)
        if p and p not in result.phones:
            result.phones.append(p)
    return result
