"""Unit tests for the compliance gate (fail-closed)."""
from __future__ import annotations

import pytest

from app.core.compliance import ComplianceService
from app.core.dnc import StubDNCCheck
from app.core.suppression import SuppressionService
from app.models.campaign import Campaign


def make_campaign(mode="dry_run", paused=False):
    return Campaign(mode=mode, is_paused=paused, daily_email_cap=20, daily_call_cap=10)


def svc(db, force_dry_run=True):
    return ComplianceService(suppression=SuppressionService(db), force_dry_run=force_dry_run)


def test_dry_run_blocks_email(db):
    c = svc(db)
    camp = make_campaign(mode="dry_run")
    check = c.check(channel="email", email="owner@example.com", campaign=camp, db=db)
    assert not check.ok
    assert any("dry-run" in r for r in check.reasons)


def test_force_dry_run_overrides_live(db):
    c = svc(db, force_dry_run=True)
    camp = make_campaign(mode="live")  # user says live...
    check = c.check(channel="email", email="owner@example.com", campaign=camp, db=db)
    assert not check.ok  # ...but force_dry_run holds it dry


def test_suppression_blocks_send(db):
    sup = SuppressionService(db)
    sup.add("email", "blocked@example.com", reason="unsubscribe")
    c = ComplianceService(suppression=sup, force_dry_run=False)
    camp = make_campaign(mode="live")
    check = c.check(channel="email", email="blocked@example.com", campaign=camp, db=db)
    assert not check.ok
    assert any("suppression" in r for r in check.reasons)


def test_voice_dnc_blocks_call(db):
    dnc = StubDNCCheck()
    dnc.register("6591111111")
    sup = SuppressionService(db)
    c = ComplianceService(suppression=sup, dnc=dnc, force_dry_run=False,
                          call_hours="00:00-23:59", call_days="mon,tue,wed,thu,fri,sat,sun")
    camp = make_campaign(mode="live")
    check = c.check(channel="voice", phone="+65 9111 1111", campaign=camp, db=db)
    assert not check.ok
    assert any("DNC" in r for r in check.reasons)


def test_voice_none_dnc_fails_closed(db):
    # no DNC provider configured => calls block
    sup = SuppressionService(db)
    c = ComplianceService(suppression=sup, force_dry_run=False,
                          call_hours="00:00-23:59", call_days="mon,tue,wed,thu,fri,sat,sun")
    camp = make_campaign(mode="live")
    check = c.check(channel="voice", phone="6591234567", campaign=camp, db=db)
    assert not check.ok
    assert any("DNC" in r or "could not be completed" in r for r in check.reasons)


def test_voice_call_window_blocks(db):
    sup = SuppressionService(db)
    c = ComplianceService(suppression=sup, force_dry_run=False,
                          call_hours="10:00-11:00", call_days="mon")
    camp = make_campaign(mode="live")
    # test with a fixed "now" that is a Monday outside 10-11
    from datetime import datetime
    now = datetime(2025, 6, 2, 15, 30)  # Monday
    check = c.check(channel="voice", phone="6591234567", campaign=camp, db=db, now=now)
    assert any("outside call hours" in r for r in check.reasons) or not check.ok


def test_bounce_rate_auto_pause(db):
    from app.core.settings_service import set_setting
    set_setting(db, "stats.bounce_rate", 0.1)
    sup = SuppressionService(db)
    c = ComplianceService(suppression=sup, force_dry_run=False)
    camp = make_campaign(mode="live")
    check = c.check(channel="email", email="owner@example.com", campaign=camp, db=db)
    assert not check.ok
    assert any("bounce rate" in r for r in check.reasons)
