from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base, GUID, TimestampMixin

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    name: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(String(64), default="Singapore")
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    categories: Mapped[list] = mapped_column(JSONType, default=list)
    daily_email_cap: Mapped[int] = mapped_column(Integer, default=20)
    daily_call_cap: Mapped[int] = mapped_column(Integer, default=10)
    send_window: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="dry_run")
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False)
