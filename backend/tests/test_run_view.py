"""M6: run-view endpoint returns pipeline stage breakdown + apify runs."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db import override_session_factory
from app.models.base import Base
from app.models.lead import Lead
from app.models.apify_run import ApifyRun
from app.models.job import Job


def _mk_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TS = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    override_session_factory(TS)
    from app.main import app
    c = TestClient(app)
    return c, TS


def _seed(c, TS):
    import datetime
    r = c.post("/campaigns", json={"name": "Run View Test", "country": "SG", "city": "Orchard", "categories": ["Clinic"]})
    assert r.status_code == 200, r.text
    camp_id = r.json()["id"]
    with TS() as s:
        s.add(Lead(id="lead-1", campaign_id=camp_id, source="osm", source_place_id="p:a", name="Place A", status="enriched"))
        s.add(Lead(id="lead-2", campaign_id=camp_id, source="osm", source_place_id="p:b", name="Place B", status="discovered"))
        s.add(ApifyRun(id="ar-1", campaign_id=camp_id, actor_id="actor/x", search="clinic", status="done", items_fetched=10, leads_imported=2, estimated_cost_usd=0.5, created_at=datetime.datetime.utcnow()))
        s.add(Job(id="job-1", lead_id="lead-1", stage="enrich", status="succeeded"))
        s.commit()
    return camp_id


def test_runs_endpoint_pipeline_stages():
    c, TS = _mk_client()
    camp_id = _seed(c, TS)
    r = c.get("/campaigns/" + camp_id + "/runs")
    assert r.status_code == 200
    b = r.json()
    assert b.get("apify_runs") is not None
    assert isinstance(b["stages"], list) and len(b["stages"]) == 6
    assert b["stages"][1]["stage"] == "enrich" and b["stages"][1]["count"] == 1
    assert b["active_runs"] == []
    assert len(b["apify_runs"]) == 1 and b["apify_runs"][0]["status"] == "done"
    override_session_factory(None)


def test_runs_endpoint_active_run_reported():
    c, TS = _mk_client()
    camp_id = _seed(c, TS)
    with TS() as s:
        s.add(ApifyRun(id="ar-2", campaign_id=camp_id, actor_id="actor/x", search="clinic", status="running", items_fetched=3, leads_imported=0))
        s.commit()
    b = c.get("/campaigns/" + camp_id + "/runs").json()
    assert "running" in b["active_runs"]
    assert len(b["apify_runs"]) == 2
    override_session_factory(None)


def test_runs_404():
    c, TS = _mk_client()
    r = c.get("/campaigns/nope/runs")
    assert r.status_code == 404
    override_session_factory(None)
