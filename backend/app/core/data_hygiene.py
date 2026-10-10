"""Data-hygiene scanner used by the pre-commit hook (and tests).

Goal: real-looking contact data must never reach the repository. A pre-commit
hook (see scripts/check_contact_data.py) runs this over staged text files and
fails the commit when it finds an email or phone that is NOT an allowed fake
placeholder, or when a staged image lives under /evidence or is named p6-*.

Allowlists (the only values that may appear in the repo):
- emails whose domain is example.com / example.org / example.net (and subdomains)
- phone numbers that are obviously fake sample placeholders:
  * +65 0000 style (Singapore demo format, e.g. "+65 0000 0000")
  * fictional US 555-01xx / 000-0000 prefixes
  * dates (YYYY-MM-DD), YYYYMMDD model ids, and IP addresses
  * bare digit runs that are part of a URL slug/path (e.g. a lead id suffix)

Everything else (a gmail address, a real-looking mobile number) is flagged.
"""
from __future__ import annotations

import re
from datetime import date

# Domains and their subdomains are allowed sample placeholders.
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net")
ALLOWED_EMAIL_TLDS = {".test", ".invalid", ".localhost"}

_SINGAPORE_DEMO_RE = re.compile(r"\+?65[\s-]?0{4,}")
_US_555_RE = re.compile(r"\(?555\)?[\s-]?0?1\d\d")
_ALL_ZERO_RE = re.compile(r"^0[\s0-9]{7,}$")
_DATE_RE = re.compile(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}")
_DATE8_RE = re.compile(r"^\d{8}$")
_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_YEAR_RANGE_RE = re.compile(r"^\d{4}-\d{2,8}$")  # year-version ids (e.g. CVE-2025-66478)

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Compact standalone phone-like token: optional +, optional (area), digit groups
# separated by space/hyphen/paren. Kept as a *candidate*; find_violations filters.
PHONE_TOKEN_RE = re.compile(r"(?<!\w)[+]?\(?\d{1,4}\)?[\s.-]*\d{2,4}[\s.-]*\d{2,4}(?:[\s.-]*\d{1,4})?")


def _looks_like_date_or_id(token: str) -> bool:
    t = token.strip()
    if _DATE_RE.search(t):
        return True
    m = _DATE8_RE.match(t)
    if m:
        try:
            d = m.group(0)
            y, mo, dd = int(d[:4]), int(d[4:6]), int(d[6:8])
            date(y, mo, dd)
            return True
        except ValueError:
            return False
    return False


def is_allowed_email(email: str) -> bool:
    low = email.strip().lower()
    if "@" not in low:
        return False
    domain = low.rsplit("@", 1)[1]
    if domain in ALLOWED_EMAIL_DOMAINS:
        return True
    for base in ALLOWED_EMAIL_DOMAINS:
        if domain.endswith("." + base):
            return True
    return any(low.endswith(s) for s in ALLOWED_EMAIL_TLDS)


def is_allowed_phone(token: str) -> bool:
    t = token.strip()
    if _looks_like_date_or_id(t):
        return True  # dates / model ids are not phones
    if _IPV4_RE.match(t):
        return True  # IP address is not a phone number
    if _SINGAPORE_DEMO_RE.search(t) or _US_555_RE.search(t):
        return True
    if _ALL_ZERO_RE.match(t):
        return True
    digits = re.sub(r"[^\d]", "", t)
    return bool(digits) and all(ch == "0" for ch in digits)


def find_violations(text: str) -> list[dict]:
    """Return [{kind, value}] for real-looking emails and phone numbers.

    Phone heuristic (kept tight to avoid false positives on code):
    - the token must have >= 7 digits
    - it must NOT contain a "." (decimals/versions/floats are not phones)
    - it must be a standalone token (not glued to letters/digits)
    - it must look contacty: a leading "+", or a group separator
    """
    out: list[dict] = []
    for m in EMAIL_RE.finditer(text):
        if not is_allowed_email(m.group(0)):
            out.append({"kind": "email", "value": m.group(0)})
    for m in PHONE_TOKEN_RE.finditer(text):
        tok = m.group(0).strip().strip("()-.,;:")
        if not tok or is_allowed_phone(tok):
            continue
        digits = re.sub(r"[^\d]", "", tok)
        if len(digits) < 7:
            continue
        if "." in tok:
            continue  # decimal / version / float
        if _YEAR_RANGE_RE.match(tok):
            continue  # year/version ids like CVE-2025-66478 or 2025-66478
        # adjacency: not glued to a letter/digit on either side
        before = text[m.start() - 1] if m.start() > 0 else ""
        after = text[m.end()] if m.end() < len(text) else ""
        if before.isalnum() or after.isalnum():
            continue
        # must look phone-like: leading +, or a group separator inside
        if not (tok.startswith("+") or any(c in tok for c in " ()-–")):
            continue
        # a bare digit run directly after / or - is a URL slug/path, not a phone
        if before in ("/", "-") and tok.isdigit():
            continue
        out.append({"kind": "phone", "value": tok})
    return out


def staged_image_is_evidence(path: str) -> bool:
    p = path.replace("\\", "/")
    basename = p.rsplit("/", 1)[-1]
    return ("/evidence/" in p or p.startswith("evidence/")) or basename.startswith("p6-")
