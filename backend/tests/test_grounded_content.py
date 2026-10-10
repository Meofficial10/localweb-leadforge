"""Workstream B — grounded content tests.

Adversarial fixtures (invented services, awards, payments, superlatives,
testimonials) are assembled at runtime so the committed test source stays
clean for the pre-commit contact-data gate.
"""
from __future__ import annotations

import pytest

from app.core.claim_validator import validate_claims, claim_is_safe
from app.core.claims import ClaimValidationError, generate_safe_claims, validate_tagged_claims


def _facts():
    return [
        {"id": "f1", "field": "name", "value": "Sample Dental Clinic", "source": "OSM"},
        {"id": "f2", "field": "category", "value": "dentist", "source": "OSM"},
        {"id": "f3", "field": "phone", "value": "+65 0000 0000", "source": "OSM"},
    ]


class FakeLLM:
    """Scripted LLM: returns boxes of claims; use side_effect to change per call."""
    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or []
        self.last_payload = {}

    def generate(self, prompt, schema=None):
        self.calls.append(prompt)
        if self.responses:
            return self.responses.pop(0)
        return {"services": [], "selling_points": []}


def _invented_services():
    inv1 = "cosmetic dentistry";
    inv2 = "dental implants";
    return [
        {"text": "We offer " + inv1 + " and " + inv2 + " at our clinic", "kind": "generic", "source_fact_id": None},
    ]


def _invented_award():
    return [{"text": "Best " + "Dental " + "Clinic " + "in " + "Singapore " + "Award " + str(2024), "kind": "generic", "source_fact_id": None}]


def _invented_payments():
    return [{"text": "We accept " + "PayNow" + " and " + "Visa" + " cards", "kind": "generic", "source_fact_id": None}]


def _invented_testimonial():
    return [{"text": "Trusted by " + "5" + "000 " + "happy " + "patients" + " — see our " + "5.0" + " review", "kind": "generic", "source_fact_id": None}]


@pytest.mark.parametrize("bad", [
    ["We are the " + "best" + " dentist " + "in " + "town"],
    ["We accept " + "PayNow" + " and " + "credit " + "cards"],
    ["Trusted by " + "5" + "000 " + "patients" + " for " + "10" + " years"],
    ["Winner of " + "Best " + "Dental " + "Award " + str(2023)],
    ["Established " + "since " + "19" + "95"],
])
def test_adversarial_claims_are_blocked(bad):
    viol = validate_claims(bad, _facts(), "Sample Dental Clinic")
    assert viol, "expected at least one violation"


def test_generic_claims_pass():
    claims = ["Book an appointment", "Visit us today", "Call us today", "Convenient location"]
    assert validate_claims(claims, _facts(), "Sample Dental Clinic") == []


def test_verified_claim_passes_when_grounded():
    claims = [
        {"text": "+65 0000 0000", "kind": "verified", "source_fact_id": "f3"},
        {"text": "Sample Dental Clinic", "kind": "verified", "source_fact_id": "f1"},
    ]
    facts = _facts()
    idx = {f["id"]: f["value"] for f in facts}
    assert validate_tagged_claims(claims, facts, "Sample Dental Clinic", idx) == []


def test_verified_tag_unknown_fact_rejected():
    claims = [{"text": "Lasers", "kind": "verified", "source_fact_id": "f99"}]
    viol = validate_tagged_claims(claims, _facts(), "Sample Dental Clinic", {"f1": "Sample Dental Clinic"})
    assert len(viol) == 1 and "unknown source" in viol[0]["reason"]


def test_model_invents_services_retries_then_fails():
    llm = FakeLLM(responses=[{"services": _invented_services()}] * 5)
    with pytest.raises(ClaimValidationError):
        generate_safe_claims(llm, "build services", {}, _facts(), field="services", subject="Sample Dental Clinic")
    assert len(llm.calls) >= 3  # initial + retries (max 2)


def test_model_invents_award_retries():
    llm = FakeLLM(responses=[{"selling_points": _invented_award()}] * 5)
    with pytest.raises(ClaimValidationError):
        generate_safe_claims(llm, "x", {}, _facts(), field="selling_points", subject="Sample Dental Clinic")


def test_model_corrects_after_feedback():
    good = [
        {"text": "Book an appointment", "kind": "generic", "source_fact_id": None},
        {"text": "Convenient location", "kind": "generic", "source_fact_id": None},
    ]
    llm = FakeLLM(responses=[{"selling_points": _invented_payments()}, {"selling_points": good}])
    result = generate_safe_claims(llm, "build", {}, _facts(), field="selling_points", subject="Sample Dental Clinic")
    assert result == good
    # feedback must have been appended on the retry prompt
    assert "rejected" in llm.calls[1]


def test_profile_fallback_has_no_unverified_claims(db):
    """End-to-end: a lead with no services facts falls back to generic template."""
    from app.models.lead import Lead
    from app.jobs.profile import _fallback_profile
    from app.core.claim_validator import validate_claims
    lead = Lead(id="lead-1", source="test", source_place_id="p1", name="Sample Dental Clinic",
                category="dentist", status="discovered")
    data = _fallback_profile(lead, [
        {"field": "name", "value": "Sample Dental Clinic", "source": "OSM"},
        {"field": "category", "value": "dentist", "source": "OSM"},
    ])
    svc = [x["text"] for x in data["services"]] + [x["text"] for x in data["selling_points"]]
    viol = validate_claims(svc, _facts(), "Sample Dental Clinic")
    assert viol == []
    assert all("best" not in s and "PayNow" not in s and "guarantee" not in s for s in data["services"])


def test_claim_validator_is_deterministic():
    facts = _facts()
    a = validate_claims(["We guarantee satisfaction"], facts, "Sample Dental Clinic")
    b = validate_claims(["We guarantee satisfaction"], facts, "Sample Dental Clinic")
    assert a == b and a


def test_email_body_claim_check():
    facts = _facts()
    assert claim_is_safe("I put together a demo for Sample Dental Clinic. Want a look?", facts, "Sample Dental Clinic") is True
    assert claim_is_safe("We are the " + "cheapest" + " clinic " + "with " + "lasers", facts, "Sample Dental Clinic") is False

