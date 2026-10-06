"""Runtime-editable settings stored in the DB `settings` table.

Keys override the corresponding env/default values. Values are JSONB. This is
how the kill switch, per-channel pause and budget caps are stored so a dashboard
can flip them without redeploying.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings_meta import SettingKV

DEFAULT_SETTINGS: dict[str, Any] = {
    "system.paused": False,
    "channel.email.paused": False,
    "channel.voice.paused": False,
    "budget.places.monthly_cap": 1000.0,
    "budget.llm.monthly_cap": 500.0,
    "budget.voice.monthly_cap": 0.0,
    "warmup.started_at": None,
    "stats.bounce_rate": 0.0,
    "stats.complaint_rate": 0.0,
}


def get_setting(db: Session, key: str, default: Any = None) -> Any:
    row = db.execute(select(SettingKV).where(SettingKV.key == key)).scalar_one_or_none()
    if row is None:
        return DEFAULT_SETTINGS.get(key, default)
    return row.value.get("value", default)


def set_setting(db: Session, key: str, value: Any) -> None:
    row = db.execute(select(SettingKV).where(SettingKV.key == key)).scalar_one_or_none()
    if row is None:
        row = SettingKV(key=key, value={"value": value})
        db.add(row)
    else:
        row.value = {"value": value}
    db.commit()


def is_system_paused(db: Session) -> bool:
    return bool(get_setting(db, "system.paused", False))


def is_channel_paused(db: Session, channel: str) -> bool:
    return bool(get_setting(db, f"channel.{channel}.paused", False))
