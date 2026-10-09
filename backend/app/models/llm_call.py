from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from app.models.base import Base, GUID

JSONType = JSON().with_variant(SQLiteJSON(), "sqlite")


class LLMCall(Base):
    """Every LLM generation: purpose (profile/demo/draft/test/playground), provider,
    model, latency, token usage, status, error and actual prompt/response, so the AI
    activity page can show what was generated and with which model."""
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer().with_variant(BigInteger, "postgresql"), primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(GUID, nullable=True, index=True)
    lead_id: Mapped[str | None] = mapped_column(GUID, nullable=True, index=True)
    purpose: Mapped[str] = mapped_column(String(24), default="test", index=True)
    provider: Mapped[str] = mapped_column(String(32), default="test")
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="ok")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
