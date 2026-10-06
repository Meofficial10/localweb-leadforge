"""Integration test: end-to-end dry-run pipeline with mocked providers.

Asserts that discovery -> enrichment -> profile -> demo build -> draft all produce
artifacts while NOTHING is sent (dry-run default).
"""
from __future__ import annotations

from app.core.state_machine import transition  # noqa: F401
from app.jobs.discovery import discover_campaign
from app.jobs.enrichment import run_enrichment_for_campaign
from app.jobs.profile import build_profile
from app.jobs.build_demo import build_demo
from app.jobs.send import prepare_email_message
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.sources.base import Place


class FakeSource:
    name = "fake"

    def search(self, city, categories):
        # category-aware: each category query returns the matching place
        table = {
            "salon": Place(source="fake", source_place_id="p1", name="Salon One", category="salon",
                           address="1 Orchard", rating=4.5, review_count=12),
            "cafe": Place(source="fake", source_place_id="p2", name="Cafe Two", category="cafe",
                          website="https://cafetwo.com", rating=4.0),
            "repair": Place(source="fake", source_place_id="p3", name="Repair Works", category="repair",
                            address="2 Bukit", rating=4.8),
        }
        return [table[c] for c in categories if c in table]


def test_discovery_filters_website_and_dedupes(db):
    camp = Campaign(id="c1", name="T1", city="Singapore", categories=["salon", "repair"],
                    mode="dry_run", daily_email_cap=20, daily_call_cap=10)
    db.add(camp)
    db.commit()

    # run twice => idempotent dedupe
    r1 = discover_campaign(db, camp, adapters=[FakeSource()])
    r2 = discover_campaign(db, camp, adapters=[FakeSource()])

    assert r1["found"] == 2
    assert r1["no_website"] == 2  # both salon + repair have no website
    assert r1["inserted"] == 2  # p1, p3 (cafe not in categories, and cafe has a website anyway)
    assert r2["inserted"] == 0  # dedupe by (source, source_place_id)
    assert db.query(Lead).count() == 2
    # only no-website leads stored, all has_website=False
    assert all(l.has_website is False for l in db.query(Lead).all())


def test_pipeline_through_demo_ready_and_draft(db):
    camp = Campaign(id="c2", name="T2", city="Singapore", categories=["salon"],
                    mode="dry_run", daily_email_cap=20, daily_call_cap=10)
    db.add(camp)
    db.commit()
    discover_campaign(db, camp, adapters=[FakeSource()])
    leads = db.query(Lead).all()
    assert leads, "expected discovered leads"

    # Fake enrichment: attach an email contact manually (no network)
    from app.models.contact import Contact
    from app.utils import new_uuid
    lead = leads[0]
    db.add(Contact(id=new_uuid(), lead_id=lead.id, kind="email",
                   value="owner@salon.com", source_url="https://facebook.com/search/top?q=Salon"))
    lead.contact_type = "email"
    lead.status = transition("discovered", "enriched")
    db.commit()

    from app.llm.mock import MockLLM
    profile = build_profile(db, lead, llm=MockLLM())
    assert profile.services
    assert profile.brand

    site = build_demo(db, lead)
    assert site is not None
    assert site.preview_url
    assert "Demo preview" in open(site.html_path, encoding="utf-8").read()

    msg = prepare_email_message(db, lead, camp)
    assert msg is not None
    assert msg.status == "draft"
    assert msg.body
    # dry-run: must NOT be sent
    assert msg.provider_message_id is None
    assert msg.sent_at is None
