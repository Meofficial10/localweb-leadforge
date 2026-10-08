from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, GUID


class ApifyRun(Base):
    """Tracks an Apify actor run started on behalf of a campaign.

    status: queued | running | fetching | done | failed
    We also store the estimated USD cost and the Apify run id so the campaign run
    view can show progress and budget usage without re-polling Apify.
    """

    __tablename__ = "apify_runs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=lambda: __import__('uuid').uuid4().__str__())
    campaign_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("campaigns.id"), nullable=True)
    apify_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    search: Mapped[str | None] = mapped_column(Text, nullable=True)  # city + category context sent to the actor
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    leads_imported: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
