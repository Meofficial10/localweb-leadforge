"""Unit tests for contact extraction and normalisation."""
from __future__ import annotations

from app.enrichment.extractor import extract_contacts
from app.utils import normalize_email, normalize_phone


def test_extract_email_from_mailto():
    html = '<a href="mailto:hello@salon.com?subject=x">Email</a>'
    r = extract_contacts(html)
    assert "hello@salon.com" in r.emails


def test_extract_email_plain():
    html = "Contact us at owner@repair.sg today."
    r = extract_contacts(html)
    assert "owner@repair.sg" in r.emails


def test_ignore_email_in_script():
    html = "<script>var x='fake@example.invalid'</script><p>info@cafe.sg</p>"
    r = extract_contacts(html)
    assert "info@cafe.sg" in r.emails
    assert "fake@example.invalid" not in r.emails


def test_normalize_email():
    assert normalize_email("  Owner@Salon.COM ") == "owner@salon.com"


def test_normalize_phone_sg():
    assert normalize_phone("9111 2222") == "6591112222"  # local SG -> +65 prefix
    assert normalize_phone("6591112222") == "6591112222"
