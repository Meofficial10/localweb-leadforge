"""ENRICH stage: find a public email/phone from the listing, public social About
pages, and public directories. Records source URL for each contact and classifies
the lead as email / phone / both / none.
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.state_machine import transition
from app.enrichment.extractor import Extraction, extract_contacts
from app.enrichment.fetcher import FetchedPage, PageFetcher
from app.models.lead import Lead
from app.models.contact import Contact
from app.utils import new_uuid

_NAME_SLUG_RE = re.compile(r"[^a-z0-9]+")


def build_candidate_urls(lead: Lead) -> list[str]:
    """Public search/directory URLs derived from the business name only."""
    name = (lead.name or "").strip()
    if not name:
        return []
    slug = _NAME_SLUG_RE.sub("", name.lower())
    return [
        "https://www.facebook.com/search/top?q={name}".format(name=name.replace(" ", "%20")),
        "https://www.instagram.com/{slug}/".format(slug=slug),
        "https://www.google.com/search?q={q}".format(q=name.replace(" ", "+") + "+contact"),
    ]


class EnrichmentService:
    def __init__(self, fetcher: PageFetcher | None = None):
        self.fetcher = fetcher or PageFetcher()

    def enrich(self, db: Session, lead: Lead) -> dict:
        """Contact a lead. Returns classification and counts."""
        if lead.contacts:
            return {"classification": lead.contact_type or "none", "already": True}

        emails: list[str] = []
        phones: list[str] = []
        sources: dict[tuple[str, str], str] = {}

        def absorb(page: FetchedPage | None, source_url: str) -> None:
            if page is None:
                return
            ex: Extraction = extract_contacts(page.html)
            for e in ex.emails:
                if e not in emails:
                    emails.append(e)
                    sources[("email", e)] = source_url
            for p in ex.phones:
                if p not in phones:
                    phones.append(p)
                    sources[("phone", p)] = source_url

        # Also attempt a direct site probe if the source gave us a non-null website
        # (discovery filter normally means none; this is defensive).
        if lead.raw_website:
            absorb(self.fetcher.fetch(lead.raw_website), lead.raw_website)

        for url in build_candidate_urls(lead):
            absorb(self.fetcher.fetch(url), url)

        for e in dict.fromkeys(emails):
            db.add(Contact(id=new_uuid(), lead_id=lead.id, kind="email", value=e,
                           source_url=sources.get(("email", e)), verified=False))
        for p in dict.fromkeys(phones):
            db.add(Contact(id=new_uuid(), lead_id=lead.id, kind="phone", value=p,
                           source_url=sources.get(("phone", p)), verified=False))

        has_email = len(emails) > 0
        has_phone = len(phones) > 0
        cls = "both" if (has_email and has_phone) else ("email" if has_email else ("phone" if has_phone else "none"))

        lead.contact_type = cls
        lead.status = transition(lead.status, "enriched" if (has_email or has_phone) else "no_contact")
        db.commit()
        record(db, action="enrich_lead", lead_id=lead.id, detail={
            "classification": cls, "emails": len(emails), "phones": len(phones)})
        return {"emails": len(emails), "phones": len(phones), "classification": cls}
