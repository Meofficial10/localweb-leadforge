"""Location endpoints for the campaign wizard (Step 2).

Serves the bundled offline country -> state -> city dataset. No external API calls.
The dataset lives in app/data/geo/<CODE>.json and is lazy-loaded per country so we
never ship the whole world up front.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/locations", tags=["locations"])

GEO_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "geo"

def _load(code: str) -> dict:
    f = GEO_DIR / (code.upper() + ".json")
    if not f.exists():
        raise FileNotFoundError(code)
    return json.loads(f.read_text(encoding="utf-8"))


@router.get("/countries")
def list_countries():
    """Country list with flag + code from the bundled index."""
    f = GEO_DIR / "countries.json"
    if not f.exists():
        return {"countries": []}
    data = json.loads(f.read_text(encoding="utf-8"))
    return {"countries": data["countries"]}


@router.get("/{code}/states")
def list_states(code: str):
    try:
        data = _load(code)
    except FileNotFoundError:
        raise HTTPException(404, f"location data not available for {code}")
    return {"states": [s["state"] for s in data["states"]]}


@router.get("/{code}/cities")
def list_cities(code: str, state: str = ""):
    try:
        data = _load(code)
    except FileNotFoundError:
        raise HTTPException(404, f"location data not available for {code}")
    bodies = data["states"]
    if state:
        body = next((s for s in bodies if s["state"].lower() == state.strip().lower()), None)
        if body is None:
            # fall back to everything when the state name is a free-form override
            cities = [c for s in bodies for c in s["cities"]]
            return {"cities": sorted(set(cities))}
        return {"cities": body["cities"]}
    cities = [c for s in bodies for c in s["cities"]]
    return {"cities": sorted(set(cities))}