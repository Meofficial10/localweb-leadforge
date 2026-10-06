"""Unit tests for the rate limiter (daily caps + per-domain throttle)."""
from __future__ import annotations

from app.core.rate_limiter import RateLimiter


def test_daily_email_cap():
    rl = RateLimiter(daily_email_cap=3, daily_call_cap=2)
    assert rl.consume_email()
    assert rl.consume_email()
    assert rl.consume_email()
    assert not rl.consume_email()
    assert rl.remaining_email() == 0


def test_per_domain_throttle():
    rl = RateLimiter(daily_email_cap=100, max_per_domain_per_hour=2)
    assert rl.consume_email("example.com")
    assert rl.consume_email("example.com")
    assert not rl.consume_email("example.com")
    assert rl.consume_email("other.com")  # different domain unaffected


def test_daily_call_cap():
    rl = RateLimiter(daily_email_cap=10, daily_call_cap=2)
    assert rl.consume_call()
    assert rl.consume_call()
    assert not rl.consume_call()
    assert rl.remaining_call() == 0


def test_check_does_not_consume():
    rl = RateLimiter(daily_email_cap=1)
    assert rl.check_email()
    assert rl.check_email()  # check only peeks
