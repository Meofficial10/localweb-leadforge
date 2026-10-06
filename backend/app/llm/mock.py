"""Deterministic mock LLM for tests and offline development."""
from __future__ import annotations

import random
from typing import Any

from app.llm.base import LLMProvider


class MockLLM(LLMProvider):
    name = "mock"

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def generate(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        # Return a plausible structured profile from the input business name
        import re
        m = re.search(r"business[\s]*([^\n]+)", prompt, re.IGNORECASE)
        biz = (m.group(1).strip() if m else "The Business")
        # pull services hint from "category" if present
        cat_m = re.search(r"category[\s]*([^\n]+)", prompt, re.IGNORECASE)
        cat = (cat_m.group(1).strip() if cat_m else "local business").lower()
        theme = _theme_for(cat)
        return {
            "summary": f"{biz} is a well-regarded {cat} in the local neighbourhood.",
            "services": [f"{cat.title()} service", "Walk-ins welcome", "Friendly advice"],
            "tone": "warm and professional",
            "selling_points": ["Local and approachable", "Trusted by regulars", "Convenient location"],
            "brand": {"colors": THEMES[theme]["colors"], "theme": theme},
            "usps_used_in_email": ["Local and approachable"],
        }


THEMES = {
    "warm": {"colors": ["#B76E79", "#F7EDE8", "#5A3A3A"], "plate": "salonspa"},
    "bold": {"colors": ["#1F3D5C", "#E8F0F7", "#F2A900"], "plate": "repair"},
    "fresh": {"colors": ["#4F8A5B", "#F4FAF5", "#2E3A3B"], "plate": "cafe"},
    "elegant": {"colors": ["#7A5C88", "#FDF7F2", "#3E2C44"], "plate": "florist"},
}


def _theme_for(cat: str) -> str:
    if any(k in cat for k in ("salon", "spa", "beauty", "barber")):
        return "warm"
    if any(k in cat for k in ("repair", "trade", "plumb", "auto")):
        return "bold"
    if any(k in cat for k in ("cafe", "bakery", "restaurant", "food")):
        return "fresh"
    if any(k in cat for k in ("florist", "boutique", "gift")):
        return "elegant"
    return "fresh"
