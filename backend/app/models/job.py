from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    lead_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)  # discover|enrich|profile|build|draft|send|call|followup
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|succeeded|failed|dead_letter
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
