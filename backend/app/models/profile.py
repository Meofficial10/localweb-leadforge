from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.models.base import Base, GUID

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class Profile(Base):
    __tablename__ = "profiles"

    lead_id: Mapped[str] = mapped_column(GUID, ForeignKey("leads.id", ondelete="CASCADE"), primary_key=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    services: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    selling_points: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    brand: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    raw_inputs: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    lead = relationship("Lead", back_populates="profile")
