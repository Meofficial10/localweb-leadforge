"""Email warm-up ramp: linear ramp from a low start volume up to the campaign cap."""
from __future__ import annotations


def daily_cap_for_day(day_index: int, *, start: int, target: int, days: int = 21) -> int:
    """day_index 0-based (0 = first day). Linear ramp from start to target."""
    if days <= 1:
        return target
    frac = min(max(day_index / (days - 1), 0.0), 1.0)
    return int(round(start + (target - start) * frac))


def ramped_cap(schedule: dict | None, *, target: int, day_index: int | None = None) -> int:
    """Apply a warm_up_schedule: {"mode": "ramp", "start": 5, "days": 21, "target": 20}."""
    if not schedule or schedule.get("mode", "ramp") != "ramp":
        return target
    start = int(schedule.get("start", 5))
    days = int(schedule.get("days", 21))
    tgt = int(schedule.get("target", target) or target)
    idx = day_index if day_index is not None else 0
    return daily_cap_for_day(idx, start=start, target=tgt, days=days)
