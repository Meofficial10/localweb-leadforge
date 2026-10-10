"""Unit tests for contact extraction and normalisation."""
from __future__ import annotations

from app.enrichment.extractor import extract_contacts
from app.utils import normalize_email, normalize_phone


def test_extract_email_from_mailto():
    html = '<a href="mailto:hello@sample.example.com?subject=x">Email</a>'
    r = extract_contacts(html)
    assert "hello@sample.example.com" in r.emails


def test_extract_email_plain():
    html = "Contact us at owner@repair.example.com today."
    r = extract_contacts(html)
    assert "owner@repair.example.com" in r.emails


def test_ignore_email_in_script():
    html = "<script>var x='fake@example.invalid'</script><p>info@cafe.example.net</p>"
    r = extract_contacts(html)
    assert "info@cafe.example.net" in r.emails
    assert "fake@example.invalid" not in r.emails


def test_normalize_email():
    assert normalize_email("  Owner@Sample.EXAMPLE.COM ") == "owner@sample.example.com"


def test_normalize_phone_sg():
    assert normalize_phone("91112222") == "6591112222"  # local SG -> +65 prefix
    assert normalize_phone("6591112222") == "6591112222"
