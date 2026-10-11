"""Workstream D: pipeline coverage tests.

Every lead advances through ALL stages in one run; drafts are appropriate to
contact type (email -> email draft, phone-only -> WhatsApp/text + call-script
drafts), no-contact leads reach terminal no_contact with reason + sources tried,
and the run summary shows counts per stage AND per reason.

All fixtures are fake (example.com / +65 0000-style numbers) - no real data.
"""
from __future__ import annotations

from app.core.state_machine import transition
from app.jobs.pipeline import run_campaign_once, _draft_phone_outreach
from app.jobs.enrichment import run_enrichment_for_campaign
from app.jobs.discovery import discover_campaign
from app.models.campaign import Campaign
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.message import Message
from app.sources.base import Place
from app.utils import new_uuid

class FakeSource:
    name = "fake"
    def search(self, city, categories, country="Singapore", radius_m=3000.0):
        table = {
            "salon": Place(source="fake", source_place_id="p1", name="Salon One", category="salon",
                           address="1 Orchard", rating=4.5, review_count=12,
                           phone="+65 0000 1111", email="hi@example.com"),
            "cafe": Place(source="fake", source_place_id="p2", name="Cafe Two", category="cafe",
                          website="https://cafetwo.example.com", rating=4.0),
            "repair": Place(source="fake", source_place_id="p3", name="Repair Works", category="repair",
                            address="2 Bukit", rating=4.8, phone="+65 0000 2222"),
            "dental": Place(source="fake", source_place_id="p4", name="Dental Clinic", category="dental",
                            address="1 Raffles", rating=4.9, email=None, phone=None),
        }
        return [table[c] for c in categories if c in table]

def _camp(db, cid="c1"):
    camp = Campaign(id=cid, name="T1", city="Singapore", categories=["salon", "cafe", "repair", "dental"],
                    mode="dry_run", daily_email_cap=20, daily_call_cap=10)
    db.add(camp)
    db.commit()
    return camp

def test_discovery_persists_contacts_and_type(db):
    camp = _camp(db)
    discover_campaign(db, camp, adapters=[FakeSource()])
    leads = {l.source_place_id: l for l in db.query(Lead).all()}
    salon = leads["p1"]  # phone + email
    assert salon.contact_type == "both"
    kinds = sorted(c.kind for c in salon.contacts)
    assert kinds == ["email", "phone"]
    for c in salon.contacts:
        assert c.source_url, "source_url per contact must be recorded"
    repair = leads["p3"]
    assert repair.contact_type == "phone"
    assert [c.kind for c in repair.contacts] == ["phone"]
    dental = leads["p4"]
    assert dental.contact_type is None
    assert dental.contacts == []

def test_no_website_leads_all_persisted(db):
    camp = _camp(db)
    r = discover_campaign(db, camp, adapters=[FakeSource()])
    assert r["inserted"] == 3  # salon, repair, dental (cafe has website)
    assert all(l.has_website is False for l in db.query(Lead).all())

def test_enrichment_transitions_preseeded_contacts(db):
    camp = _camp(db)
    discover_campaign(db, camp, adapters=[FakeSource()])
    res = run_enrichment_for_campaign(db, camp)
    assert res["enriched"] == 2
    assert res["no_contact"] == 1
    by_pid = {l.source_place_id: l for l in db.query(Lead).all()}
    assert by_pid["p1"].status == "enriched"
    assert by_pid["p3"].status == "enriched"
    d = by_pid["p4"]
    assert d.status == "no_contact"
    assert d.no_contact_reason
    assert isinstance(d.enrichment_sources, list) and d.enrichment_sources

def test_pipeline_full_cascade_single_run(db, monkeypatch):
    camp = _camp(db)
    # seed leads directly (dedupe is global; discovery already covered above)
    ts = [
        ("p1", "Salon One", "salon", "+65 0000 1111", "hi@example.com"),
        ("p3", "Repair Works", "repair", "+65 0000 2222", None),
        ("p4", "Dental Clinic", "dental", None, None),
    ]
    for pid, name, cat, phone, email in ts:
        lead = Lead(id=new_uuid(), campaign_id=camp.id, source="fake", source_place_id=pid,
                    name=name, category=cat, has_website=False, status="discovered")
        db.add(lead)
        if phone: db.add(Contact(lead_id=lead.id, kind="phone", value=phone, source_url="https://example.com/phone", verified=False))
        if email: db.add(Contact(lead_id=lead.id, kind="email", value=email, source_url="https://example.com/email", verified=False))
    db.commit()
    # mock the LLM resolver so profile generation uses MockLLM (deterministic, no real model)
    import app.jobs.profile as profile_mod
    from app.llm.mock import MockLLM
    def fake_resolve_llm(sess):
        svc = MockLLM()
        svc.db = sess
        return svc, "mock", "mock"
    monkeypatch.setattr(profile_mod, "resolve_llm", fake_resolve_llm)
    summary = run_campaign_once(db, camp)
    leads = {l.source_place_id: l for l in db.query(Lead).all()}
    salon = leads["p1"]
    assert salon.status in ("queued_email", "contacted")
    msgs = [m for m in salon.messages if m.channel == "email"]
    assert msgs and msgs[0].status == "draft"
    repair = leads["p3"]
    assert repair.status in ("queued_call", "contacted")
    chans = sorted(m.channel for m in repair.messages)
    assert "voice" in chans and "whatsapp" in chans
    dental = leads["p4"]
    assert dental.status == "no_contact"
    assert dental.no_contact_reason
    assert summary["demo_built"] >= 2
    assert summary["enriched"] >= 2
    assert summary["no_contact"] >= 1
    assert summary["reasons"], "expected per-reason counts"
def test_phone_draft_has_ai_disclosure_and_dnc(db):
    camp = _camp(db)
    discover_campaign(db, camp, adapters=[FakeSource()])
    repair = next(l for l in db.query(Lead).all() if l.source_place_id == "p3")
    repair.status = transition("discovered", "enriched")
    db.commit()
    d = _draft_phone_outreach(db, repair, camp)
    assert d["call_script"] is True
    assert d["chat"] is True
    msgs = {m.channel: m for m in db.query(Message).filter(Message.lead_id == repair.id).all()}
    wa = msgs.get("whatsapp")
    assert wa and "AI disclosure" in wa.body
    assert "DNC" in wa.body
    assert wa.status == "draft"
    voice = msgs.get("voice")
    assert voice and "Call script" in voice.subject
    assert "AI assistant" in (voice.body or "")
    assert "DNC" in (voice.body or "")

def test_run_summary_counts_per_stage_and_reason(db):
    camp = _camp(db)
    discover_campaign(db, camp, adapters=[FakeSource()])
    res = run_enrichment_for_campaign(db, camp)
    assert "reasons" in res
    assert res["reasons"], "batch enrichment must record no-contact reasons"
    assert res["enriched"] == 2
    assert res["no_contact"] == 1
