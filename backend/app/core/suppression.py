"""Global suppression list. Checked before every outbound email and call.

Unsubscribe / "stop" is honored instantly and permanently per the compliance rules.
The DB-backed repo is the single source of truth; a small in-memory cache is used
to make the hot check fast and failure-closed (a cache miss hits the DB).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.suppression import Suppression


@dataclass
class SuppressionService:
    db: Session
    _email_cache: set[str] = field(default_factory=set)
    _phone_cache: set[str] = field(default_factory=set)
    _domain_cache: set[str] = field(default_factory=set)
    _loaded: bool = False

    def _load(self) -> None:
        if self._loaded:
            return
        rows = self.db.execute(select(Suppression.kind, Suppression.value)).all()
        for kind, value in rows:
            value = value.strip().lower()
            if kind == "email":
                self._email_cache.add(value)
            elif kind == "phone":
                self._phone_cache.add(value)
            elif kind == "domain":
                self._domain_cache.add(value)
        self._loaded = True

    def _domain_of(self, email: str) -> str:
        return email.split("@", 1)[-1].lower() if "@" in email else ""

    def is_suppressed(self, *, email: str | None = None, phone: str | None = None) -> bool:
        """Fail-closed: returns True if there is ANY suppression match."""
        self._load()
        if email:
            e = email.strip().lower()
            if e in self._email_cache:
                return True
            if self._domain_of(e) in self._domain_cache:
                return True
        if phone:
            p = phone.strip().lower()
            if p in self._phone_cache:
                return True
        return False

    def add(self, kind: str, value: str, reason: str | None = None) -> None:
        """Add to suppression. Idempotent via unique constraint."""
        value = value.strip()
        existing = self.db.execute(
            select(Suppression).where(
                Suppression.kind == kind, Suppression.value == value
            )
        ).scalar_one_or_none()
        if existing is None:
            self.db.add(Suppression(kind=kind, value=value, reason=reason))
            self.db.commit()
        # update cache
        v = value.lower()
        if kind == "email":
            self._email_cache.add(v)
        elif kind == "phone":
            self._phone_cache.add(v)
        elif kind == "domain":
            self._domain_cache.add(v)

    def remove(self, kind: str, value: str) -> bool:
        value = value.strip()
        res = self.db.execute(
            delete(Suppression).where(
                Suppression.kind == kind, Suppression.value == value
            )
        )
        self.db.commit()
        v = value.lower()
        if kind == "email":
            self._email_cache.discard(v)
        elif kind == "phone":
            self._phone_cache.discard(v)
        elif kind == "domain":
            self._domain_cache.discard(v)
        return res.rowcount > 0

    def list_all(self) -> list[Suppression]:
        return list(self.db.execute(select(Suppression)).scalars().all())
