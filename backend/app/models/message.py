from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    lead_id: Mapped[str] = mapped_column(GUID, ForeignKey("leads.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(16), nullable=False)  # email
    direction: Mapped[str] = mapped_column(String(16), default="outbound")
    sequence_step: Mapped[int] = mapped_column(Integer, default=1)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|queued|approved|sent|failed|bounced|replied|opted_out
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)

    lead = relationship("Lead", back_populates="messages")
