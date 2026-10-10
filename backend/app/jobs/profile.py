"""PROFILE stage: LLM turns verified facts only into a structured JSON profile
(services, tone, selling points, brand colors). Every generated claim carries a
kind tag (verified | generic) and optional source_fact_id. Claims that aren't
grounded in verified facts are retried then fall back to a deterministic template.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.claims import ClaimValidationError, generate_safe_claims
from app.core.facts import collect_verified_facts, facts_to_prompt_block
from app.core.state_machine import transition
from app.llm.base import LLMSchemaError
from app.llm.factory import resolve_llm
from app.models.lead import Lead
from app.models.profile import Profile
from app.utils import new_uuid  # noqa: F401

PROFILE_SCHEMA = {
    "type": "object",
    "required": ["summary", "services", "tone", "selling_points", "brand"],
    "properties": {
        "summary": {"type": "string"},
        "services": {"type": "array", "items": {
            "type": "object",
            "required": ["text", "kind", "source_fact_id"],
            "properties": {
                "text": {"type": "string"},
                "kind": {"type": "string", "enum": ["verified", "generic"]},
                "source_fact_id": {"type": ["string", "null"]},
            },
        }},
        "tone": {"type": "string"},
        "selling_points": {"type": "array", "items": {
            "type": "object",
            "required": ["text", "kind", "source_fact_id"],
            "properties": {
                "text": {"type": "string"},
                "kind": {"type": "string", "enum": ["verified", "generic"]},
                "source_fact_id": {"type": ["string", "null"]},
            },
        }},
        "brand": {
            "type": "object",
            "required": ["colors", "theme"],
            "properties": {
                "colors": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                "theme": {"type": "string"},
            },
        },
    },
}

_FALLBACK_SERVICES = [
    {"text": "Contact us for details", "kind": "generic"},
    {"text": "Book an appointment", "kind": "generic"},
]
_FALLBACK_SELLING = [
    {"text": "Convenient location", "kind": "generic"},
    {"text": "Visit us today", "kind": "generic"},
]


def _facts_to_dicts(facts_rows) -> list[dict]:
    return [{"id": f.id, "field": f.field, "value": f.value,
             "source": f.source, "is_null_fact": f.is_null_fact} for f in facts_rows]


def _fallback_profile(lead: Lead, fact_dicts: list[dict]) -> dict:
    category = next((f["value"] for f in fact_dicts if f["field"] == "category"), lead.category or "local business")
    return {
        "summary": f"{lead.name or 'Our business'} is a {category} in the local area.",
        "services": list(_FALLBACK_SERVICES),
        "tone": "friendly and professional",
        "selling_points": list(_FALLBACK_SELLING),
        "brand": {"colors": ["#3E8E5A", "#F5FAF6", "#26332B"], "theme": "fresh"},
    }


def build_profile(db: Session, lead: Lead, llm=None) -> Profile:
    # 1. verified facts are collected and are the ONLY source given to the model.
    facts_rows = collect_verified_facts(db, lead)
    fact_dicts = _facts_to_dicts(facts_rows)

    if llm is None:
        resolved = resolve_llm(db)[0]
        llm = resolved
        llm.lead_id = lead.id
    prompt = _profile_prompt(lead, fact_dicts)

    profile = db.get(Profile, lead.id)
    if profile is None:
        profile = Profile(lead_id=lead.id)
        db.add(profile)

    # 2. attempts: LLM -> retry -> deterministic fallback
    data = None
    used_fallback = False
    try:
        services = generate_safe_claims(llm, prompt + "\n\nNow write the services array.",
                                        PROFILE_SCHEMA, fact_dicts, field="services",
                                        subject=lead.name)
        selling = generate_safe_claims(llm, prompt + "\n\nNow write the selling_points array.",
                                       PROFILE_SCHEMA, fact_dicts, field="selling_points",
                                       subject=lead.name)
        brief_prompt = prompt + "\n\nNow write: summary (one neutral sentence), tone, and brand colors/theme."
        brief = llm.generate(brief_prompt, PROFILE_SCHEMA)
        data = {
            "summary": brief.get("summary") or "",
            "services": services,
            "tone": brief.get("tone") or "friendly and professional",
            "selling_points": selling,
            "brand": brief.get("brand") or {"colors": ["#3E8E5A", "#F5FAF6", "#26332B"], "theme": "fresh"},
        }
    except (LLMSchemaError, ClaimValidationError) as exc:
        used_fallback = True
        data = _fallback_profile(lead, fact_dicts)
        record(db, action="profile_fallback", lead_id=lead.id, detail={"error": str(exc)})

    profile.summary = data["summary"]
    profile.services = [s["text"] for s in data["services"]]
    profile.tone = data["tone"]
    profile.selling_points = [s["text"] for s in data["selling_points"]]
    profile.brand = data["brand"]
    profile.raw_inputs = {
        "name": lead.name,
        "category": lead.category,
        "rating": float(lead.rating) if lead.rating is not None else None,
        "review_count": lead.review_count,
        "address": lead.address,
        "facts": fact_dicts,
    }
    lead.status = transition(lead.status, "profiled")
    db.commit()
    record(db, action="profile_built", lead_id=lead.id,
           detail={"theme": data["brand"].get("theme"), "used_fallback": used_fallback})
    return profile


def _profile_prompt(lead: Lead, fact_dicts: list[dict]) -> str:
    return (
        "You are writing the demo-website profile for a local business. "
        "You may ONLY reference the verified facts below. Every service and "
        "selling point you output MUST be tagged:\n"
        "- kind 'verified' with the source_fact_id when it comes directly from a verified fact\n"
        "- kind 'generic' for neutral category wording (e.g. 'Book an appointment', 'Visit us',\n"
        "  'Call us today', 'Convenient location') that never asserts a specific service, price,\n"
        "  year, award, certification, payment method, equipment, staff member, testimonial,\n"
        "  ranking, patient count or guarantee.\n"
        "Never invent facts. If a fact is absent from the list, do not mention it.\n"
        "\nVerified facts:\n" + facts_to_prompt_block(fact_dicts)
    )
