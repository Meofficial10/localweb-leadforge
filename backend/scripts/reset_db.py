"""Seed / reset script.

- python -m scripts.reset_db                -> reset schema (no seed)
- python -m scripts.reset_db --seed           -> reset + insert demo campaign/leads
Runs against whatever DATABASE_URL is configured. Everything is created dry-run.
"""
from __future__ import annotations

import argparse

from app.db import get_engine
from app.models.base import Base


def reset(*, seed: bool = False) -> dict:
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    if seed:
        return seed_demo_data()
    return {}


def seed_demo_data() -> dict:
    """Insert a demo campaign + sample leads in dry-run."""
    from app.db import get_sync_session
    from app.models.campaign import Campaign
    from app.models.contact import Contact
    from app.models.demo_site import DemoSite
    from app.models.lead import Lead
    from app.utils import new_uuid as new_id

    s = get_sync_session()
    try:
        camp = Campaign(
            id=new_id(),
            name="Demo Campaign - dry run",
            country="Singapore",
            city="Singapore",
            categories=["salon", "cafe", "auto repair"],
            lead_source="both",
            daily_email_cap=20,
            daily_call_cap=10,
            send_window={"start": "09:00", "end": "18:00", "days": ["mon","tue","wed","thu","fri"]},
            timezone="Asia/Singapore",
            warm_up_schedule={"mode": "ramp", "start": 5, "days": 21, "target": 20},
            followup_delay_days=4,
            approval_mode="manual",
            mode="dry_run",
            is_paused=False,
        )
        s.add(camp)
        s.flush()

        leads_data = [
            ("Bluewater Salon", "salon", "Orchard Road", "salon@blueware.example.com", "+6590000001"),
            ("Corner Cafe", "cafe", "Tanjong Pagar", "hi@cornercafe.example.com", "+6590000002"),
            ("Swift Repairs", "auto repair", "Jurong East", "service@swiftrepairs.example.com", "+6590000003"),
        ]
        made = 0
        for (name, cat, area, email, phone) in leads_data:
            lid = new_id()
            lead = Lead(
                id=lid,
                campaign_id=camp.id,
                source="osm",
                source_place_id="seed-" + lid[:8],
                name=name,
                category=cat,
                address=area + ", Singapore",
                has_website=True,
                raw_website="https://" + email.split("@")[1],
                contact_type="both",
                status="discovered",
            )
            s.add(lead)
            s.add(Contact(id=new_id(), lead_id=lid, kind="email", value=email, ))
            s.add(Contact(id=new_id(), lead_id=lid, kind="phone", value=phone, ))
            made += 1

        # A lead that is already demo-ready, so the queue has a real draft to approve.
        ready_id = new_id()
        ready = Lead(
            id=ready_id,
            campaign_id=camp.id,
            source="osm",
            source_place_id="seed-ready-" + ready_id[:8],
            name="Bluewater Spa (ready)",
            category="spa",
            address="Orchard Road, Singapore",
            has_website=True,
            raw_website="https://bluewaterspa.example",
            contact_type="both",
            status="demo_ready",
        )
        s.add(ready)
        s.add(Contact(id=new_id(), lead_id=ready_id, kind="email", value="bookings@bluewaterspa.example.com", source_url="https://bluewaterspa.example/contact"))
        s.add(Contact(id=new_id(), lead_id=ready_id, kind="phone", value="+6590000999", source_url="https://bluewaterspa.example/contact"))
        s.add(DemoSite(id=new_id(), lead_id=ready_id, template="spa", preview_url="https://demo.leadforge.example/bluewater-spa", deploy_status="live", version=1))
        from app.jobs.send import prepare_email_message
        prepare_email_message(s, ready, camp)
        made += 1
        s.commit()
        return {"campaigns": 1, "leads": made}
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset/seed LeadForge database")
    parser.add_argument("--seed", action="store_true", help="Seed demo data after reset")
    args = parser.parse_args()
    counts = reset(seed=args.seed)
    if args.seed:
        print("Seeded:", counts)
    else:
        print("Database reset. No seed.")


if __name__ == "__main__":  # type: ignore[attr-defined]  # pragma: no cover
    main()