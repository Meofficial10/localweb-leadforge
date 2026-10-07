from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class IntegrationSecret(Base):
    """Encrypted, write-only secret store for third-party API keys/tokens.

    Values are AES-GCM (Fernet) encrypted at rest with a key derived from
    SECRET_KEY. They are never returned to the browser; only a masked preview
    and booleans (is_set / last_verified) are exposed via the API.
    """

    __tablename__ = "integration_secrets"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)  # e.g. places.api_key
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)  # Fernet token
    is_set: Mapped[bool] = mapped_column(default=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())


class DemoProject(Base):
    """Hosting project reference for demo deploys (e.g. CF Pages project / Netlify site)."""

    __tablename__ = "demo_projects"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # cloudflare_pages | netlify | local
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
