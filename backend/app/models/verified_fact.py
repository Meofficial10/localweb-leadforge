"""Verified facts: the only ground truth an LLM prompt may reference.

Each row is one verified fact about a lead (name, category, address, phone,
email, hours, website, rating, review_count, social, services, opening_hours).
Every row carries the source it came from (e.g. OSM node id, "no website" ->
"n/a") and a timestamp so we can distinguish "verified" from "generated copy"
(which lives in Profile and is never trusted for facts).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class VerifiedFact(Base):
    __tablename__ = "verified_facts"
    __table_args__ = (UniqueConstraint("lead_id", "field", "value", name="uq_vfacts_lead_field_value"),)

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__("uuid").uuid4().__str__())
    lead_id: Mapped[str] = mapped_column(GUID, ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(Text, nullable=False)  # name | category | address | phone | email | website | rating | review_count | hours | social | services | opening_hours
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)  # OSM node / url / "n/a" / human
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    is_null_fact: Mapped[bool] = mapped_column(Boolean, default=False)  # true when website=none style

    lead = relationship("Lead", back_populates="verified_facts")
