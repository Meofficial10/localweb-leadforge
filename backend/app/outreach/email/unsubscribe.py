"""Public unsubscribe page + instant permanent suppression."""
from __future__ import annotations

from urllib.parse import urlencode

from app.config import settings
from app.utils import sign


def unsubscribe_url(lead_id: str, message_id: str) -> str:
    token = sign(f"{lead_id}:{message_id}", settings.secret_key)
    return f"{settings.unsubscribe_base_url}/u?{urlencode({'l': lead_id, 'm': message_id, 't': token})}"
