"""Compliance service: the single gate for any outbound action.

compliance.check(lead, channel) must pass before ANY email or call. It fails
closed: every sub-check must pass.

Checks (all must hold):
  - kill switch not active (system + channel)
  - campaign not paused and mode permits the channel (dry_run blocks real send)
  - global suppression list clear (email / phone / domain)
  - rate limiter has budget (daily caps + per-domain throttle)
  - call hours window + weekdays (voice only)
  - DNC check (voice, Singapore) — must be completed and clear
  - auto-pause gates: if bounce/complaint rate thresholds are exceeded, sending pauses

Returns (ok: bool, reasons: list) so callers can surface why a send was blocked.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.core.dnc import DNCRegistry, DNCUnavailable
from app.core.rate_limiter import RateLimiter
from app.core.settings_service import get_setting, is_channel_paused, is_system_paused
from app.core.suppression import SuppressionService
from app.utils import normalize_phone


@dataclass
class ComplianceCheck:
    ok: bool
    reasons: list[str] = field(default_factory=list)


class ComplianceService:
    def __init__(
        self,
        suppression: SuppressionService,
        dnc: DNCRegistry | None = None,
        call_hours: str = "10:00-18:00",
        call_days: str = "mon,tue,wed,thu,fri",
        force_dry_run: bool = True,
    ):
        self.suppression = suppression
        self.dnc = dnc or DNCRegistry()
        self.call_hours = call_hours
        self.call_days = set(call_days.split(","))
        self.force_dry_run = force_dry_run
        # rate limiter instance per campaign would normally be injected
        self.rate_limiters: dict[str, RateLimiter] = {}

    # ---- helpers ----

    def _in_call_window(self, now: datetime | None = None) -> bool:
        now = now or datetime.now()
        if now.strftime("%a").lower()[:3] not in {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}:
            pass
        day = now.strftime("%a").lower()
        if day not in self.call_days:
            return False
        try:
            start_s, end_s = self.call_hours.split("-")
            sh, sm = map(int, start_s.split(":"))
            eh, em = map(int, end_s.split(":"))
            minutes = now.hour * 60 + now.minute
            return (sh * 60 + sm) <= minutes < (eh * 60 + em)
        except ValueError:
            return False

    def _domain_of(self, email: str) -> str:
        return email.split("@", 1)[-1].lower() if "@" in email else ""

    # ---- main gate ----

    def check(
        self,
        *,
        channel: str,
        email: str | None = None,
        phone: str | None = None,
        campaign=None,
        db=None,
        allow_list: bool = True,
        now: datetime | None = None,
    ) -> ComplianceCheck:
        reasons: list[str] = []

        # 1. kill switch + channel pause
        if db is not None:
            if is_system_paused(db):
                reasons.append("system paused (kill switch)")
            if is_channel_paused(db, channel):
                reasons.append(f"channel {channel} paused")
        if campaign is not None and getattr(campaign, "is_paused", False):
            reasons.append("campaign paused")

        # 2. dry-run default: LIVE mode must be explicitly enabled
        mode = getattr(campaign, "mode", "dry_run") if campaign is not None else "dry_run"
        if self.force_dry_run or mode == "dry_run":
            reasons.append(f"channel {channel} in dry-run mode")

        # 3. suppression check
        if allow_list:
            if email and self.suppression.is_suppressed(email=email):
                reasons.append("email on suppression list")
            if phone and self.suppression.is_suppressed(phone=normalize_phone(phone)):
                reasons.append("phone on suppression list")

        # 4. rate limit
        rl = self._rl_for(channel, campaign)
        if rl is not None:
            if channel == "email":
                if email and not rl.check_email(self._domain_of(email)):
                    reasons.append("daily email cap or domain throttle reached")
            else:
                if not rl.check_call():
                    reasons.append("daily call cap reached")

        # 5. voice-only checks
        if channel == "voice" or channel == "call":
            if phone:
                if not self._in_call_window(now):
                    reasons.append("outside call hours window")
                try:
                    if not self.dnc.check(phone):
                        reasons.append("phone on DNC registry (or DNC check failed)")
                except DNCUnavailable as exc:
                    reasons.append(f"dnc check could not be completed: {exc}")

        # 6. bounce/complaint auto-pause (read from DB settings if available)
        if db is not None:
            br = float(get_setting(db, "stats.bounce_rate", 0.0) or 0.0)
            cr = float(get_setting(db, "stats.complaint_rate", 0.0) or 0.0)
            if br >= 0.05:
                reasons.append("bounce rate above auto-pause threshold")
            if cr >= 0.001:
                reasons.append("complaint rate above auto-pause threshold")

        return ComplianceCheck(ok=len(reasons) == 0, reasons=reasons)

    def _rl_for(self, channel: str, campaign) -> RateLimiter | None:
        caps = (20, 10)
        if campaign is not None:
            caps = (getattr(campaign, "daily_email_cap", 20) or 20,
                    getattr(campaign, "daily_call_cap", 10) or 10)
        key = (channel, caps)
        if key not in self.rate_limiters:
            self.rate_limiters[key] = RateLimiter(
                daily_email_cap=caps[0], daily_call_cap=caps[1]
            )
        return self.rate_limiters[key]

    def block_reason_string(self, check: ComplianceCheck) -> str:
        return "; ".join(check.reasons) if check.reasons else ""
