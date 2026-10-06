from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    lead_id: Mapped[str] = mapped_column(GUID, ForeignKey("leads.id", ondelete="CASCADE"))
    provider_call_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    dnc_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_disclosed: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    lead = relationship("Lead", back_populates="calls")
