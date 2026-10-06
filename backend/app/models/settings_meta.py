from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class SettingKV(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONType, nullable=False)
