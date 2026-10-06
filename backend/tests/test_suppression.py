"""Unit tests for the global suppression list."""
from __future__ import annotations

from app.core.suppression import SuppressionService
from app.models.suppression import Suppression


def _svc(db):
    return SuppressionService(db)


def test_is_suppressed_email(db):
    svc = _svc(db)
    svc.add("email", "owner@example.com", reason="unsubscribe")
    svc._loaded = False  # force reload from DB path
    assert svc.is_suppressed(email="OWNER@example.com")
    assert not svc.is_suppressed(email="other@example.com")


def test_is_suppressed_domain(db):
    svc = _svc(db)
    svc.add("domain", "example.com", reason="bounce")
    assert svc.is_suppressed(email="anything@example.com")
    assert not svc.is_suppressed(email="anything@example.org")


def test_is_suppressed_phone(db):
    svc = _svc(db)
    svc.add("phone", "6591234567", reason="dnc")
    assert svc.is_suppressed(phone="6591234567")
    assert not svc.is_suppressed(phone="6598765432")


def test_add_is_idempotent(db):
    svc = _svc(db)
    svc.add("email", "a@b.com")
    svc.add("email", "a@b.com")
    rows = db.query(Suppression).all()
    assert len(rows) == 1


def test_remove(db):
    svc = _svc(db)
    svc.add("email", "a@b.com")
    assert svc.is_suppressed(email="a@b.com")
    assert svc.remove("email", "a@b.com")
    assert not svc.is_suppressed(email="a@b.com")
