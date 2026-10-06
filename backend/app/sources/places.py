"""Google Places API adapter (official API).

Requires GOOGLE_PLACES_API_KEY. Falls back gracefully to nothing when no key is set so
the OSM adapter can take over. Never scrapes Google Maps HTML.
"""
from __future__ import annotations

import math

import httpx

from app.config import settings
from app.sources.base import Place, SourceAdapter

# https://developers.google.com/maps/documentation/places/web-service/search-text
_TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


class GooglePlacesAdapter(SourceAdapter):
    name = "places"

    def __init__(self, api_key: str | None = None, client: httpx.Client | None = None):
        self.api_key = api_key or settings.places_api_key
        self.client = client or httpx.Client(timeout=30)

    def search(self, city: str, categories: list[str]) -> list[Place]:
        if not self.api_key:
            return []
        places: list[Place] = []
        for cat in categories:
            query = f"{cat} in {city}"
            resp = self.client.get(
                _TEXT_SEARCH_URL,
                params={"query": query, "key": self.api_key},
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("results", []):
                pid = item.get("place_id")
                if not pid:
                    continue
                # fetch details for website/phone fields (fields param limits cost)
                detail = self._details(pid)
                website = (detail.get("website") or "").strip() or None
                places.append(
                    Place(
                        source=self.name,
                        source_place_id=pid,
                        name=item.get("name", ""),
                        category=cat,
                        address=item.get("formatted_address"),
                        rating=_num(item.get("rating")),
                        review_count=_num(item.get("user_ratings_total")),
                        lat=_num((item.get("geometry") or {}).get("location", {}).get("lat")),
                        lng=_num((item.get("geometry") or {}).get("location", {}).get("lng")),
                        website=website,
                        phone=(detail.get("international_phone_number") or "").strip() or None,
                        raw={"place_id": pid, "types": item.get("types", [])},
                    )
                )
        return places

    def _details(self, place_id: str) -> dict:
        try:
            resp = self.client.get(
                _DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": "website,international_phone_number",
                    "key": self.api_key,
                },
            )
            resp.raise_for_status()
            return resp.json().get("result", {})
        except Exception:  # noqa: BLE001 - missing details should not kill discovery
            return {}


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
        if math.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None
