"""PROFILE stage: LLM turns name/category/rating/reviews/hours/photos into a
structured JSON profile (services, tone, selling points, brand colors)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.state_machine import transition
from app.llm.base import LLMSchemaError
from app.llm.service import LLMService
from app.models.lead import Lead
from app.models.profile import Profile
from app.utils import new_uuid  # noqa: F401

PROFILE_SCHEMA = {
    "type": "object",
    "required": ["summary", "services", "tone", "selling_points", "brand"],
    "properties": {
        "summary": {"type": "string"},
        "services": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "tone": {"type": "string"},
        "selling_points": {"type": "array", "items": {"type": "string"}, "minItems": 1},
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


def build_profile(db: Session, lead: Lead, llm: LLMService | None = None) -> Profile:
    llm = llm or LLMService()
    prompt = _profile_prompt(lead)
    raw_inputs = {
        "name": lead.name,
        "category": lead.category,
        "rating": float(lead.rating) if lead.rating is not None else None,
        "review_count": lead.review_count,
        "address": lead.address,
    }
    try:
        data = llm.generate(prompt, PROFILE_SCHEMA)
    except LLMSchemaError as exc:
        # don't kill the lead; record failure and leave in enriched state
        record(db, action="profile_failed", lead_id=lead.id, detail={"error": str(exc)})
        raise

    profile = db.get(Profile, lead.id)
    if profile is None:
        profile = Profile(lead_id=lead.id)
        db.add(profile)
    profile.summary = data["summary"]
    profile.services = data["services"]
    profile.tone = data["tone"]
    profile.selling_points = data["selling_points"]
    profile.brand = data["brand"]
    profile.raw_inputs = raw_inputs
    lead.status = transition(lead.status, "profiled")
    db.commit()
    record(db, action="profile_built", lead_id=lead.id, detail={"theme": data["brand"].get("theme")})
    return profile


def _profile_prompt(lead: Lead) -> str:
    return (
        "Create a structured business profile for the demo website.\n"
        f"business: {lead.name}\n"
        f"category: {lead.category or ''}\n"
        f"rating: {lead.rating or ''}\n"
        f"reviews: {lead.review_count or ''}\n"
        f"address: {lead.address or ''}\n"
        "Do not invent services, prices, or awards. Keep selling points generic and safe."
    )
