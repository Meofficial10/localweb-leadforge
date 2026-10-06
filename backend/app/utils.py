from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-()]{5,20}[0-9]$")


def new_uuid() -> str:
    return str(uuid.uuid4())


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value.strip()))


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    digits = re.sub(r"[^0-9]", "", value)
    if digits.startswith("0"):
        digits = digits[1:]
    # 8-digit SG mobile -> prefix with 65
    if len(digits) == 8:
        return "65" + digits
    return digits


def make_consent_token(lead_id: str, message_id: str) -> str:
    return secrets.token_urlsafe(24)


def sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
