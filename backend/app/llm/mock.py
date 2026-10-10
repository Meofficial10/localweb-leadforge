"""Deterministic mock LLM for tests and offline development.

Grounded: the mock only emits claims it can tag as "generic" (neutral category
wording) and never invents specific services/facts. This keeps pipeline tests
deterministic AND compliant with the Workstream B rule that generated copy must
not assert unverified facts.
"""
from __future__ import annotations

import random
import re
from typing import Any

from app.llm.base import LLMProvider


class MockLLM(LLMProvider):
    name = "mock"

    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)
        self.last_payload = {}

    def generate(self, prompt: str, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        facts = self._extract_facts(prompt)
        m = re.search(r"business: ([^\n]+)", prompt)
        biz = (m.group(1).strip() if m else "The Business")
        cat_m = re.search(r"category: ([^\n]+)", prompt)
        cat = (cat_m.group(1).strip() if cat_m else "local business").lower()
        theme = _theme_for(cat)
        # only generic ph: the validator requires generic claims from whitelist
        services = [
            {"text": g, "kind": "generic", "source_fact_id": None}
            for g in ("Book an appointment", "Visit us", "Contact us for details")
        ]
        selling_pts = [
            {"text": g, "kind": "generic", "source_fact_id": None}
            for g in ("Convenient location", "Call us today")
        ]
        summary = f"{biz} is a {cat} in the local area."
        return {
            "summary": summary,
            "services": services,
            "tone": "warm and professional",
            "selling_points": selling_pts,
            "brand": {"colors": THEMES[theme]["colors"], "theme": theme},
        }

    def _extract_facts(self, prompt: str) -> list[dict]:
        """Parse the Verified facts block from a prompt into dicts."""
        facts = []
        m = re.search(r"business: ([^\n]+)", prompt)
        block = re.search(r"Verified facts:[\s\S]*?(?=\n\nNow|$)", prompt)
        if block:
            for line in block.group(0).strip().splitlines():
                line = line.strip()
                if not line.startswith("- "):
                    continue
                m2 = re.match(r"- ([\w ]+): (.*?) \[source: (.*?)\](?: \(absent\))?$", line)
                if m2:
                    facts.append({"field": m2.group(1).strip(), "value": m2.group(2).strip(),
                                  "source": m2.group(3).strip(), "is_null_fact": False,
                                  "id": f"fact-{len(facts)+1}"})
        return facts


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
    if any(k in cat for k in ("dentist", "clinic", "doctor")):
        return "fresh"
    if any(k in cat for k in ("florist", "boutique", "gift")):
        return "elegant"
    return "fresh"
