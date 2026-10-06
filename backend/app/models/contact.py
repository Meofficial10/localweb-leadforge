from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("lead_id", "kind", "value", name="uq_contacts_lead_kind_value"),)

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    lead_id: Mapped[str] = mapped_column(GUID, ForeignKey("leads.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # email | phone | website
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    found_at: Mapped[datetime] = mapped_column(default=func.now())

    lead = relationship("Lead", back_populates="contacts")
