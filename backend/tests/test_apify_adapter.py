"""M3: Apify adapter — start run, poll with backoff, fetch dataset, normalize, dedupe."""
from __future__ import annotations
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import override_session_factory
from app.models.base import Base

@pytest.fixture()
def client_b(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    override_session_factory(TestSession)
    from app.main import app
    c = TestClient(app)
    yield c, monkeypatch, TestSession
    override_session_factory(None)


RUN_JSON = {"id": "R_123", "status": "RUNNING", "defaultDatasetId": "DS_9", "usageUsd": 0.42}
DONE_JSON = {"id": "R_123", "status": "SUCCEEDED", "defaultDatasetId": "DS_9", "usageUsd": 0.42}
ITEMS = [
    {"title": "Bloom Salon", "placeId": "Pl001", "categoryName": "Beauty salon",
     "address": "1 Orchard Rd", "latitude": 1.3, "longitude": 103.8, "rating": 4.6,
     "reviewsCount": 210, "phone": "+65 6000 0001", "website": "https://bloomsalon.example"},
    {"title": "Quiet Nail Bar", "placeId": "Pl002", "categoryName": "Nail salon",
     "address": "2 Orchard Rd", "latitude": 1.31, "longitude": 103.81, "rating": 4.4,
     "reviewsCount": 88, "phone": "+65 6000 0002"},
]


class FakeClient:
    def __init__(self, items=ITEMS, done=True):
        self.posts = []; self.gets = []; self.items = items; self.done = done
    def post(self, url, params=None, json=None, content=None, headers=None, data=None):
        self.posts.append(url)
        return type("R", (), {"status_code": 200, "json": lambda _: {"data": RUN_JSON}, "raise_for_status": lambda _: None})()
    def get(self, url, params=None):
        self.gets.append(url)
        if "actor-runs" in url:
            return type("R", (), {"status_code": 200, "json": lambda _: {"data": DONE_JSON if self.done else RUN_JSON}, "raise_for_status": lambda _: None})()
        if "items" in url:
            return type("R", (), {"status_code": 200, "json": lambda _: ITEMS, "raise_for_status": lambda _: None})()
        return type("R", (), {"status_code": 200, "json": lambda _: {"data": {}}, "raise_for_status": lambda _: None})()


def _set_up(c):
    c.post("/integrations/secrets", json={"key": "apify.api_token", "value": "tok_123"}).status_code == 200
    c.post("/integrations/apify/configure", json={"values": {"actor_id": "dSCLg0N4nXrK6omlg", "max_results": 25, "timeout_sec": 300, "monthly_budget_cap": 10.0}})


def test_apify_search_normalizes_and_filters(client_b):
    c, mp, TS = client_b
    _set_up(c)
    fc = FakeClient(); fc.done = True
    from app.sources.apify import ApifyAdapter
    db = TS()
    ad = ApifyAdapter(db=db, campaign_id=None, client=fc)
    places = ad.search("Singapore", ["salon"])
    db.close()
    assert fc.posts and any("/actor/" in p and "/runs" in p for p in fc.posts)
    assert len(places) == 2
    by_id = {p.source_place_id: p for p in places}
    assert by_id["Pl001"].website == "https://bloomsalon.example"
    assert by_id["Pl002"].website is None
    assert by_id["Pl002"].rating == 4.4 and by_id["Pl002"].review_count == 88
    assert by_id["Pl002"].source == "apify"


def test_apify_run_row_tracks_status_and_cost(client_b):
    c, mp, TS = client_b
    _set_up(c)
    fc = FakeClient(); fc.done = True
    from app.sources.apify import ApifyAdapter
    from app.models.apify_run import ApifyRun
    db = TS()
    ad = ApifyAdapter(db=db, campaign_id="camp_1", client=fc)
    ad.search("Singapore", ["salon"])
    row = db.query(ApifyRun).first()
    assert row is not None
    assert row.status == "done"
    assert row.items_fetched == 2
    assert row.estimated_cost_usd == pytest.approx(0.42)
    assert row.campaign_id == "camp_1"
    db.close()


def test_apify_bad_token_returns_clear_error(client_b):
    c, mp, TS = client_b
    from app.sources.apify import ApifyAdapter
    db = TS()
    ad = ApifyAdapter(db=db, client=FakeClient())
    places = ad.search("Singapore", ["salon"])  # no token configured
    from app.models.apify_run import ApifyRun
    row = db.query(ApifyRun).first()
    assert places == []
    assert row is not None and row.status == "failed"
    assert "token" in (row.error or "").lower()
    db.close()


def test_discovery_uses_apify_and_dedupes(client_b):
    c, mp, TS = client_b
    _set_up(c)
    camp = c.post("/campaigns", json={"name": "AP1", "city": "Singapore", "categories": ["salon"], "lead_sources": ["apify"]}).json()
    assert camp["lead_sources"] == ["apify"]
    from app.jobs.discovery import discover_campaign
    db = TS()
    from app.models.campaign import Campaign
    cobj = db.get(Campaign, camp["id"])
    from app.sources.apify import ApifyAdapter
    res = discover_campaign(db, cobj, adapters=[ApifyAdapter(db=db, campaign_id=cobj.id, client=FakeClient())])
    assert res["found"] == 2 and res["no_website"] == 1 and res["inserted"] == 1
    res2 = discover_campaign(db, cobj, adapters=[ApifyAdapter(db=db, campaign_id=cobj.id, client=FakeClient())])
    assert res2["inserted"] == 0
    db.close()