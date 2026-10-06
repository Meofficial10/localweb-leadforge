"""Local rate limiting: per-day caps and per-domain throttling.

v1 uses an in-process counter (suitable for a single worker). It is deliberately
swappable with a Redis-backed implementation for multi-worker deployments.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class DomainBudget:
    count: int = 0
    window_start: int = 0


class RateLimiter:
    """Enforce daily per-channel caps and per-domain throttling."""

    def __init__(self, daily_email_cap: int = 20, daily_call_cap: int = 10,
                 max_per_domain_per_hour: int = 4, window_seconds: int = 3600):
        self.daily_email_cap = daily_email_cap
        self.daily_call_cap = daily_call_cap
        self.max_per_domain_per_hour = max_per_domain_per_hour
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._email_day = self._day_reset(0)
        self._call_day = self._day_reset(0)
        self._email_count = 0
        self._call_count = 0
        self._domains: dict[str, DomainBudget] = {}

    @staticmethod
    def _day_reset(now: float) -> int:
        # seconds since local midnight
        lt = time.localtime(now)
        return int(now - (lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec))

    def _maybe_roll(self) -> None:
        now = time.time()
        day = self._day_reset(now)
        if day != self._email_day:
            self._email_day = day
            self._email_count = 0
        if day != self._call_day:
            self._call_day = day
            self._call_count = 0
        # drop stale domain budgets
        cutoff = now - self.window_seconds
        for d in [k for k, v in self._domains.items() if v.window_start < cutoff]:
            self._domains.pop(d, None)

    def check_email(self, domain: str | None = None) -> bool:
        with self._lock:
            self._maybe_roll()
            if self._email_count >= self.daily_email_cap:
                return False
            if domain and self._domain_count(domain) >= self.max_per_domain_per_hour:
                return False
            return True

    def check_call(self) -> bool:
        with self._lock:
            self._maybe_roll()
            return self._call_count < self.daily_call_cap

    def _domain_count(self, domain: str) -> int:
        now = time.time()
        b = self._domains.get(domain)
        if b is None or b.window_start < (now - self.window_seconds):
            return 0
        return b.count

    def consume_email(self, domain: str | None = None) -> bool:
        """Attempt to consume budget; returns False if not allowed."""
        with self._lock:
            self._maybe_roll()
            if self._email_count >= self.daily_email_cap:
                return False
            if domain and self._domain_count(domain) >= self.max_per_domain_per_hour:
                return False
            self._email_count += 1
            if domain:
                now = time.time()
                b = self._domains.get(domain)
                if b is None or b.window_start < (now - self.window_seconds):
                    self._domains[domain] = DomainBudget(count=1, window_start=int(now))
                else:
                    b.count += 1
            return True

    def consume_call(self) -> bool:
        with self._lock:
            self._maybe_roll()
            if self._call_count >= self.daily_call_cap:
                return False
            self._call_count += 1
            return True

    def remaining_email(self) -> int:
        with self._lock:
            self._maybe_roll()
            return max(0, self.daily_email_cap - self._email_count)

    def remaining_call(self) -> int:
        with self._lock:
            self._maybe_roll()
            return max(0, self.daily_call_cap - self._call_count)
