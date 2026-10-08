
"""Apify source adapter: run a Google-Maps scraper actor for (city, categories), poll
the run with polite backoff (not a tight loop), fetch the dataset items, and
normalize each into the shared Place model so Apify keeps the same no-website
filter / dedupe / enrichment pipeline as Places/OSM.

https://docs.apify.com/api/v2
  POST /actor/{actorId}/runs           -> {data: {id, status, defaultDatasetId, usageUsd}}
  GET  /actor-runs/{runId}              -> {data: {status, defaultDatasetId, usageUsd}}
  GET  /datasets/{datasetId}/items     -> [ {title, address, latitude, ...} ]
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.crypto import get_secret
from app.core.settings_service import get_setting
from app.models.apify_run import ApifyRun
from app.sources.base import Place

APIFY_API = "https://api.apify.com/v2"
DEFAULT_ACTOR_ID = "dSCLg0N4nXrK6omlg"  # Google Maps Scraper (free tier)


def _num(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return None if f != f else f
    except (TypeError, ValueError):
        return None


def _int_or(v, default: int | None = None) -> int | None:
    n = _num(v)
    return int(n) if n is not None else default


class ApifyAdapter:
    """Apify lead-source adapter. Reads config from integration settings/secrets."""

    name = "apify"

    def __init__(self, *, db, campaign_id: str | None = None, api: str = APIFY_API,
                 client: httpx.Client | None = None):
        self.db = db
        self.campaign_id = campaign_id
        self.api = api
        self.client = client or httpx.Client(timeout=45)

    # ---- config plumbing -------------------------------------------------
    def _token(self) -> str | None:
        return get_secret(self.db, "apify.api_token")

    def _actor_id(self) -> str:
        return get_setting(self.db, "integration.apify.actor_id", DEFAULT_ACTOR_ID) or DEFAULT_ACTOR_ID

    def _max_results(self) -> int:
        try:
            return min(int(get_setting(self.db, "integration.apify.max_results", 100) or 100), 100)
        except (TypeError, ValueError):
            return 100

    def _run_timeout(self) -> int:
        try:
            return int(get_setting(self.db, "integration.apify.timeout_sec", 300) or 300)
        except (TypeError, ValueError):
            return 300

    # ---- Apify API calls ------------------------------------------------
    def start_run(self, actor_id: str, input_obj: dict) -> dict:
        r = self.client.post(f"{self.api}/actor/{actor_id}/runs",
                             params={"token": self._token()}, json=input_obj)
        r.raise_for_status()
        return r.json().get("data", {})

    def poll_run(self, run_id: str) -> dict:
        r = self.client.get(f"{self.api}/actor-runs/{run_id}", params={"token": self._token()})
        r.raise_for_status()
        return r.json().get("data", {})

    def fetch_items(self, dataset_id: str) -> list[dict]:
        r = self.client.get(f"{self.api}/datasets/{dataset_id}/items",
                            params={"token": self._token(), "clean": "true"})
        r.raise_for_status()
        return r.json() or []

    # ---- normalization ---------------------------------------------------
    def to_place(self, item: dict) -> Place:
        title = item.get("title") or item.get("name") or ""
        address = item.get("address")
        if isinstance(address, dict):
            address = address.get("text") or address.get("street") or address.get("full") or ""
        pid = (item.get("placeId") or item.get("place_id")
               or (str(item.get("url") or "").rsplit("/", 1)[-1]))
        website = (item.get("website") or "").strip() or None
        phone = (item.get("phone") or item.get("phoneNumber") or "").strip() or None
        return Place(
            source="apify",
            source_place_id=str(pid or ""),
            name=title,
            category=item.get("categoryName") or item.get("category"),
            address=str(address) if address else None,
            lat=_num(item.get("latitude") or item.get("lat")),
            lng=_num(item.get("longitude") or item.get("lng")),
            rating=_num(item.get("rating")),
            review_count=_int_or(item.get("reviewsCount") or item.get("reviews")),
            website=website,
            phone=phone,
            raw={k: item.get(k) for k in ("url", "cid", "categoryName", "permanentlyClosed", "isAd") if item.get(k) is not None},
        )

    # ---- run bookkeeping (ApifyRun rows for the run view) -----------------
    def _create_run(self, run_id: str | None, actor_id: str, search: str) -> ApifyRun:
        row = ApifyRun(campaign_id=self.campaign_id, apify_run_id=run_id,
                       actor_id=actor_id, search=search, status="queued")
        self.db.add(row)
        self.db.commit()
        return row

    def _update_run(self, row: ApifyRun, **kw) -> None:
        for k, v in kw.items():
            setattr(row, k, v)
        self.db.commit()

    # ---- main entry --------------------------------------------------------
    def search(self, city: str, categories: list[str]) -> list[Place]:
        """Start an actor run, poll to completion with backoff, fetch the dataset
        into Places. Returns [] (never raises) and records progress/errors in
        ApifyRun so the campaign run view can show status + estimated cost."""
        token = self._token()
        if not token:
            return _no_run(self, "Apify API token not configured")
        actor = self._actor_id()
        query = ", ".join([c for c in (categories or []) if c]) or "business"
        search_str = f"{query} in {city}"
        run = self._create_run(None, actor, f"{city} | {query}")
        self._update_run(run, status="running")

        input_obj = {
            "searchStrings": search_str,
            "maxCrawledPlacesPerSearch": self._max_results(),
            "language": "en",
            "geo:country": "SG",
            "skipClosedLocations": False,
            "maxImages": 0,
            "maxLinkTo": 0,
            "resultType": "places",
        }

        # 1) start
        try:
            data = self.start_run(actor, input_obj)
        except Exception as exc:  # noqa: BLE001
            return _no_run(self, f"Could not start actor run: {exc}", run=run)
        run_id = data.get("id")
        if not run_id:
            return _no_run(self, "Apify did not return a run id", run=run)
        self._update_run(run, apify_run_id=run_id, status="running")

        # 2) poll with backoff (2s -> 4s -> 8s -> ... capped), until done or timeout
        started = time.monotonic()
        timeout = self._run_timeout()
        delay = 2
        status = data.get("status", "ACTIVE")
        dataset_id = data.get("defaultDatasetId")
        usage = data.get("usageUsd")
        while status in ("ACTIVE", "RUNNING", "PENDING", "READY"):
            if time.monotonic() - started > timeout:
                self._update_run(run, status="failed", error="run timed out",
                                 finished_at=_now())
                return []
            time.sleep(delay)
            try:
                info = self.poll_run(run_id)
            except Exception as exc:  # noqa: BLE001
                self._update_run(run, status="failed", error=f"poll error: {exc}", finished_at=_now())
                return []
            status = info.get("status", "ACTIVE")
            dataset_id = info.get("defaultDatasetId") or dataset_id
            usage = info.get("usageUsd", usage)
            delay = min(delay * 2, 8)

        # 3) fetch dataset
        if status == "SUCCEEDED" and dataset_id:
            self._update_run(run, status="fetching")
            try:
                raw = self.fetch_items(dataset_id)
            except Exception as exc:  # noqa: BLE001
                self._update_run(run, status="failed", error=f"fetch failed: {exc}", finished_at=_now())
                return []
            places = [self.to_place(it) for it in raw]
            places = [p for p in places if p.name and p.source_place_id]
            self._update_run(run, status="done", items_fetched=len(raw),
                             leads_imported=len(places),
                             estimated_cost_usd=usage, finished_at=_now())
            return places

        # 4) terminated badly
        err = {
            "FAILED": "actor run FAILED on Apify's side",
            "ABORTED": "actor run was aborted",
            "TIMED_OUT": "actor run timed out on Apify's side",
        }.get(status, f"unexpected run status: {status}")
        self._update_run(run, status="failed", error=err, estimated_cost_usd=usage, finished_at=_now())
        return []


def _no_run(adapter: ApifyAdapter, error: str, run: ApifyRun | None = None) -> list[Place]:
    if run is not None:
        adapter._update_run(run, status="failed", error=error, finished_at=_now())
    else:
        row = ApifyRun(campaign_id=getattr(adapter, "campaign_id", None),
                       actor_id=getattr(adapter, "_actor_id", lambda: "")() or "",
                       search="", status="failed", error=error, finished_at=_now())
        adapter.db.add(row)
        adapter.db.commit()
    return []


def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)
