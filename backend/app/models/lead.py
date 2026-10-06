from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, GUID, TimestampMixin


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"
    __table_args__ = (UniqueConstraint("source", "source_place_id", name="uq_leads_source_place"),)

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    campaign_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("campaigns.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    source_place_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    lng: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    review_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_website: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_website: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="discovered", index=True)
    enriched_at: Mapped[datetime | None] = mapped_column(nullable=True)

    contacts = relationship("Contact", back_populates="lead", cascade="all, delete-orphan")
    profile = relationship("Profile", back_populates="lead", uselist=False, cascade="all, delete-orphan")
    demo_sites = relationship("DemoSite", back_populates="lead", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="lead", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="lead", cascade="all, delete-orphan")
