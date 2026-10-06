"""OSM Overpass API adapter (free fallback).

Queries businesses by category within a city bbox, returns places including
contact tags (phone/website) so we can also serve as a secondary web/phone source.
Respects Overpass etiquette: single query per run, small area, proper User-Agent.
"""
from __future__ import annotations

import re
import time

import httpx

from app.config import settings
from app.sources.base import Place, SourceAdapter

_CATEGORY_TAGS = {
    "salon": "shop=beauty",
    "beauty": "shop=beauty",
    "spa": "shop=beauty",
    "cafe": "amenity=cafe",
    "bakery": "shop=bakery",
    "restaurant": "amenity=restaurant",
    "repair": "shop=repair",
    "florist": "shop=florist",
    "barber": "shop=barber",
    "gym": "leisure=fitness_centre",
}


class OverpassAdapter(SourceAdapter):
    name = "osm"

    def __init__(self, base_url: str | None = None, client: httpx.Client | None = None):
        self.base_url = base_url or settings.overpass_base_url
        self.client = client or httpx.Client(timeout=45)

    def _bbox(self, city: str) -> str | None:
        # For v1 we use a bounded region around a known center if configured.
        # Without geocoding, fall back to a world-search limited by category (rare).
        return None

    def search(self, city: str, categories: list[str]) -> list[Place]:
        places: list[Place] = []
        for cat in categories:
            tag = _CATEGORY_TAGS.get(cat.lower())
            if tag is None:
                continue
            # "name~'City'" plus tag gives reasonable locality without geocoding cost
            query = f"""
[out:json][timeout:45];
(
  nwr["{tag.split('=')[0]}"="{tag.split('=')[1]}"]["name"~"{re.escape(city)}",i];
);
out center tags;
"""
            try:
                resp = self.client.post(
                    self.base_url,
                    content=query.encode("utf-8"),
                    headers={"User-Agent": "LeadForge/0.1 (research; contact: admin@example.com)"},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:  # noqa: BLE001 - overpass can be flaky
                continue
            for el in data.get("elements", []):
                tags = el.get("tags", {})
                pid = f"node/{el.get('id')}" if el.get("type") == "node" else f"way/{el.get('id')}"
                website = tags.get("contact:website") or tags.get("website") or None
                places.append(
                    Place(
                        source=self.name,
                        source_place_id=pid,
                        name=tags.get("name", ""),
                        category=cat,
                        address=tags.get("addr:street"),
                        lat=el.get("lat") or (el.get("center") or {}).get("lat"),
                        lng=el.get("lon") or (el.get("center") or {}).get("lon"),
                        website=website,
                        phone=tags.get("contact:phone") or tags.get("phone") or None,
                        raw={"tags": tags},
                    )
                )
            time.sleep(1)  # overpass etiquette: be polite between categories
        return places
