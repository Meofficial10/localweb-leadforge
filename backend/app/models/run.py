from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.models.base import Base, GUID

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class Run(Base):
    """One invocation of the campaign pipeline (triggered by Run now or scheduler).
    Keeps per-run summary + timing so the UI can show a live record and history."""
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__("uuid").uuid4().__str__())
    campaign_id: Mapped[str] = mapped_column(GUID, ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="running")  # running | done | failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict | None] = mapped_column(JSONType, nullable=True)  # per-stage counts + banner values
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    mode: Mapped[str | None] = mapped_column(String(16), nullable=True)  # dry_run | live (snapshot)


class RunEvent(Base):
    """A single line of the live run log: stage transition + detail + timing."""
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(GUID, ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    stage: Mapped[str] = mapped_column(String(32))  # discover | enrich | profile | demo | draft | send
    status: Mapped[str] = mapped_column(String(16))  # running | done | failed | skipped
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elapsed_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
