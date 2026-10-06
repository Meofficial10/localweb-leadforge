from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class DemoSite(Base):
    __tablename__ = "demo_sites"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    lead_id: Mapped[str] = mapped_column(GUID, ForeignKey("leads.id", ondelete="CASCADE"))
    template: Mapped[str | None] = mapped_column(String(64), nullable=True)
    html_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    deploy_status: Mapped[str] = mapped_column(String(32), default="draft")  # draft|deploying|live|failed
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    lead = relationship("Lead", back_populates="demo_sites")
