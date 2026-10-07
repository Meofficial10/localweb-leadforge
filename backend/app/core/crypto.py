"""Symmetric encryption for secrets at rest (Fernet with a key derived from SECRET_KEY)."""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    key_material = f"leadforge-secrets-v1:{settings.secret_key}".encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(key_material).digest())
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode('ascii')


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("secret cannot be decrypted (wrong SECRET_KEY?)") from exc


def mask_secret(plaintext: str | None) -> str:
    if not plaintext:
        return ""
    if len(plaintext) <= 6:
        return "•" * len(plaintext)
    return "••••••" + plaintext[-4:]


def set_secret(db, key: str, value: str) -> None:
    """Upsert (key, encrypted value)."""
    from app.models.integration_secret import IntegrationSecret
    row = db.query(IntegrationSecret).filter(IntegrationSecret.key == key).first()
    if row is None:
        row = IntegrationSecret(key=key, encrypted_value=encrypt_secret(value))
        db.add(row)
    else:
        row.encrypted_value = encrypt_secret(value)
        row.is_set = True
    db.commit()


def get_secret(db, key: str) -> str | None:
    from app.models.integration_secret import IntegrationSecret
    row = db.query(IntegrationSecret).filter(IntegrationSecret.key == key).first()
    if row is None:
        return None
    return decrypt_secret(row.encrypted_value)


def secret_meta(db, key: str) -> dict:
    from app.models.integration_secret import IntegrationSecret
    row = db.query(IntegrationSecret).filter(IntegrationSecret.key == key).first()
    if row is None:
        return {"key": key, "is_set": False, "masked": "", "last_verified_at": None}
    plain = decrypt_secret(row.encrypted_value)
    return {
        "key": key,
        "is_set": True,
        "masked": mask_secret(plain),
        "last_verified_at": str(row.last_verified_at) if row.last_verified_at else None,
    }
