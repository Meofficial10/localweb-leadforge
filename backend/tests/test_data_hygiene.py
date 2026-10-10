"""Tests for the pre-commit contact-data gate (app/core/data_hygiene.py).
Adversarial values (real-looking emails/phones) are built at runtime so the
committed test source itself never contains real contact data — matching the
repo-wide rule that tests use only fake fixtures.
"""
import pytest

from app.core.data_hygiene import (
    ALLOWED_EMAIL_TLDS,
    find_violations,
    is_allowed_email,
    is_allowed_phone,
    staged_image_is_evidence,
)


def _real_email(local, host, tld):
    return f"{local}@{host}.{tld}"


def _sg_phone(prefix, rest):
    return f"+65 {prefix} {rest}"


@pytest.mark.parametrize("email,expected", [
    ("demo@leads.example.com", True),
    ("admin@example.org", True),
    ("sub@deep.example.net", True),
    ("y@anything.test", True),
    ("z@thing.invalid", True),
    (_real_email("real", "gmail", "com"), False),
    (_real_email("jane", "hotmail", "com"), False),
    (_real_email("bob", "outlook", "com"), False),
    (_real_email("lead", "doverdental", "sg"), False),
    (_real_email("person", "company", "co.uk"), False),
])
def test_email_allowlist(email, expected):
    assert is_allowed_email(email) is expected


@pytest.mark.parametrize("phone,expected", [
    ("+65 0000 0000", True),
    ("0000 0000", True),
    ("555-0111", True),   # fictional US 555-01xx
    ("+65 0000 000" , True),
    (_sg_phone("9123", "4567"), False),
    (_sg_phone("8123", "4567"), False),
    ("6" + "523" + " " + "4567", False),  # 8-digit real-looking local
    ("+1 415 555 0100", True),  # 555-01xx fictional
    ("20240620", True),  # model id / date
    ("2023-06-01", True),  # date
    ("127.0.0.1", True),  # IP, not a phone
])
def test_phone_allowlist(phone, expected):
    assert is_allowed_phone(phone) is expected


def test_find_violations_blocks_real_contact_data():
    real_email = _real_email("jane", "gmail", "com")
    real_phone = _sg_phone("9123", "4567")
    text = (
        f"Reach out to Jane at {real_email} or call {real_phone}. "
        "See admin@example.org or +65 0000 0000."
    )
    violations = find_violations(text)
    kinds = {v["kind"] for v in violations}
    vals = [v["value"] for v in violations]
    assert "email" in kinds
    assert "phone" in kinds
    assert real_email in vals
    assert real_phone in vals
    assert "admin@example.org" not in vals
    assert "+65 0000 0000" not in vals
    for v in violations:
        if v["kind"] == "email":
            assert not is_allowed_email(v["value"])
        else:
            assert not is_allowed_phone(v["value"])


def test_allowlist_text_passes():
    text = "Contact demo@leads.example.com or chris@sample.test today. Ring +65 0000 0000."
    assert find_violations(text) == []


def test_staged_image_is_evidence():
    assert staged_image_is_evidence("evidence/p6-overview.png")
    assert staged_image_is_evidence("evidence/u7/shot.png")
    assert staged_image_is_evidence("dashboard/e2e/p6-runview.png")
    assert not staged_image_is_evidence("docs/screenshot.png")
    assert not staged_image_is_evidence("dashboard/e2e/other.png")


def test_model_ids_dates_ips_not_phones():
    text = "claude-3-5-sonnet-20240620 claude-3-haiku-20240307 version 2023-06-01 host 127.0.0.1 slug dover-91293283/"
    assert find_violations(text) == []


def test_committed_test_source_is_clean():
    """The test file itself must contain no real-looking contact data (like
    every file in the repo) — adversarial values are assembled at runtime."""
    import re
    import inspect
    src = inspect.getsource(test_email_allowlist) + inspect.getsource(test_phone_allowlist) + inspect.getsource(test_find_violations_blocks_real_contact_data)
    assert find_violations(src) == [], "test source must not contain literal real contact data"
    # the .py file itself as committed
    import pathlib
    this_file = pathlib.Path(__file__).read_text(encoding="utf-8")
    assert find_violations(this_file) == []


def test_every_tracked_file_is_clean():
    """Full repo hygiene: no tracked file contains real-looking contact data."""
    import subprocess, pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, text=True, cwd=root)
    names = [n for n in out.stdout.split(chr(0)) if n]
    bad = []
    for name in names:
        data = subprocess.run(["git", "show", ":" + name], capture_output=True, cwd=root).stdout
        if not data or b"\x00" in data[:4096]:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for v in find_violations(text):
            bad.append(f"{name}: {v['kind']} {v['value']}")
    assert bad == [], "tracked files contain real-looking contact data: " + "; ".join(bad)
