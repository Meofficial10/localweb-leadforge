"""OSM Overpass API adapter (free fallback).

Queries businesses by category within a geocoded city centre and radius, returns
places including contact tags (phone/email/website) so it can also serve as a
secondary web/phone source. Includes a mirror fallback chain and per-source
status so discovery never returns 0 silently.
"""
from __future__ import annotations

import time

import httpx

from app.config import settings
from app.sources.base import Place, SourceAdapter

_CATEGORY_TAGS = {
    "dentist": "amenity=dentist",
    "dental": "amenity=dentist",
    "dental_clinic": "amenity=dentist",
    "clinic": "amenity=clinic",
    "doctors": "amenity=doctors",
    "salon": "shop=hairdresser",
    "hairdresser": "shop=hairdresser",
    "beauty": "shop=beauty",
    "spa": "amenity=spa",
    "cafe": "amenity=cafe",
    "coffee": "amenity=cafe",
    "breakfast": "amenity=cafe",
    "bakery": "shop=bakery",
    "restaurant": "amenity=restaurant",
    "repair": "shop=repair",
    "florist": "shop=florist",
    "barber": "shop=barber",
    "gym": "leisure=fitness_centre",
    "fitness": "leisure=fitness_centre",
    "pharmacy": "amenity=pharmacy",
    "optician": "shop=optician",
    "optometrist": "shop=optician",
    "car_repair": "shop=car_repair",
    "laundry": "shop=laundry",
    "pet_grooming": "shop=pet_grooming",
    "nail": "shop=beauty",
    "massage": "shop=massage",
}

_DEFAULT_MIRRORS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


class OverpassAdapter(SourceAdapter):
    """OSM adapter: geocode city (Photon) -> query Overpass with radius,
    try mirrors in order, and expose per-search status for discovery."""

    name = "osm"

    def __init__(self, base_urls=None, timeout=45.0, client=None):
        self.base_urls = [u for u in (base_urls or []) if u] or list(_DEFAULT_MIRRORS)
        if settings.overpass_base_url not in self.base_urls:
            self.base_urls.insert(0, settings.overpass_base_url)
        self.timeout = timeout
        self.client = client or httpx.Client(timeout=timeout)
        self.last_status = None
        self.last_query = None
        self.last_http_status = None
        self.last_geocode = None

    def geocode(self, city, country="Singapore"):
        """Resolve city to (lat, lng) via Photon (free, keyless). Returns None on failure."""
        try:
            r = self.client.get("https://photon.komoot.io/api/",
                                params={"q": f"{city}, {country}", "limit": 5},
                                headers={"User-Agent": "LeadForge/0.1 (research; contact: admin@example.com)"})
            r.raise_for_status()
            js = r.json()
        except Exception:
            return None
        feats = (js or {}).get("features") or []
        if not feats:
            return None
        chosen = None
        for f in feats:
            props = f.get("properties") or {}
            if (props.get("name") or "").lower() == city.lower() and (props.get("country") or "").lower() == country.lower():
                chosen = f
                break
        if chosen is None:
            chosen = feats[0]
        try:
            lon, lat = chosen["geometry"]["coordinates"]
            return (float(lat), float(lon))
        except Exception:
            return None

    def search(self, city, categories, country="Singapore", radius_m=3000.0):
        t0 = time.monotonic()
        places = []
        reasons = []
        errors = []
        self.last_geocode = self.geocode(city, country)
        self.last_status = {"source": self.name, "ok": False, "found": 0,
                            "reasons": reasons, "errors": errors,
                            "elapsed_ms": 0}
        if self.last_geocode is None:
            reasons.append(f"Could not geocode city {city}, {country} via Photon — no coordinate for the Overpass query.")
            self.last_status["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
            return places
        lat, lon = self.last_geocode
        radius = max(int(radius_m), 500)
        used_mirror = None
        for cat in categories:
            tag = _CATEGORY_TAGS.get(cat.lower())
            if tag is None:
                reasons.append(f"No OSM tag mapping for category {cat!r}. Add a mapping or use Apify/Google.")
                continue
            k, v = tag.split("=", 1)
            q = f"[out:json][timeout:45];(nwr[{k}={v}](around:{radius},{lat},{lon}););out center tags;"
            self.last_query = q
            resp = None
            err = None
            done = False
            for mirror in self.base_urls:
                for attempt in range(2):
                    try:
                        resp = self.client.post(mirror, data={"data": q},
                                                headers={"User-Agent": "LeadForge/0.1 (research; contact: admin@example.com)"})
                        self.last_http_status = resp.status_code
                        used_mirror = mirror
                        if resp.status_code == 200:
                            done = True
                            break
                        err = f"HTTP {resp.status_code}"
                    except Exception as e:
                        err = f"{type(e).__name__}: {e}"
                    if not done:
                        time.sleep((attempt + 1))
                if done:
                    break
            if resp is None or resp.status_code != 200:
                errors.append(f"Overpass query failed for {cat!r}: {err}")
                continue
            try:
                elems = (resp.json() or {}).get("elements") or []
            except Exception as e:
                errors.append(f"Bad Overpass JSON for {cat!r}: {e}")
                continue
            if not elems:
                reasons.append(f"OSM returned 0 results for {cat!r} around {city} (radius {radius_m/1000:.1f} km). Widen the radius or add another source.")
            for el in elems:
                tags = el.get("tags") or {}
                pid = "node/" + str(el.get("id")) if el.get("type") == "node" else "way/" + str(el.get("id"))
                website = (tags.get("website") or tags.get("contact:website") or tags.get("url") or "").strip() or None
                places.append(Place(
                    source=self.name,
                    source_place_id=pid,
                    name=tags.get("name") or "",
                    category=cat,
                    address=((tags.get("addr:housenumber") or "") + " " + (tags.get("addr:street") or "")).strip() or None,
                    lat=el.get("lat") or (el.get("center") or {}).get("lat"),
                    lng=el.get("lon") or (el.get("center") or {}).get("lon"),
                    website=website,
                    phone=tags.get("phone") or tags.get("contact:phone") or None,
                    email=tags.get("email") or tags.get("contact:email") or None,
                    raw={"tags": tags},
                ))
            time.sleep(0.3)
        self.last_status["ok"] = bool(places) or bool(errors) is False and bool(reasons) is False
        self.last_status["ok"] = bool(places) or (not errors and not reasons)
        self.last_status["found"] = len(places)
        self.last_status["query"] = self.last_query
        self.last_status["http_status"] = self.last_http_status
        self.last_status["mirror"] = used_mirror
        self.last_status["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        return places
