from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class Suppression(Base):
    __tablename__ = "suppression_list"
    __table_args__ = (UniqueConstraint("kind", "value", name="uq_suppression_kind_value"),)

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # email | phone | domain
    value: Mapped[str] = mapped_column(String(256), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
