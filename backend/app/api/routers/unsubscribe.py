"""Public unsubscribe page: one click, instant permanent suppression."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.config import settings
from app.core.audit import record
from app.core.state_machine import transition
from app.core.suppression import SuppressionService
from app.db import get_session
from app.models.contact import Contact
from app.models.message import Message

router = APIRouter(tags=["public"])


@router.get("/u", response_class=HTMLResponse)
def unsubscribe_page(l: str = Query(...), m: str = Query(...), t: str = Query(...),
                     confirm: str = "0", db: Session = Depends(get_session)):
    msg = db.get(Message, m)
    emails = []
    if msg:
        lead = db.get(Contact, None)  # placeholder to keep imports used
    from app.models.lead import Lead
    lead = db.get(Lead, msg.lead_id) if msg else None
    if not lead or not msg:
        raise HTTPException(404, "Invalid unsubscribe link")
    contacts = db.execute(select(Contact).where(Contact.lead_id == lead.id, Contact.kind == "email")).scalars().all()
    emails = [c.value for c in contacts]
    if confirm == "1":
        svc = SuppressionService(db)
        for e in emails:
            svc.add("email", e.lower(), reason="unsubscribe")
            svc.add("domain", e.split("@")[-1].lower(), reason="unsubscribe")
        lead.status = transition(lead.status, "opted_out")
        db.commit()
        record(db, action="unsubscribe", lead_id=lead.id, detail={"via": "public_page", "emails": emails})
        return HTMLResponse("<h1>You are unsubscribed</h1><p>You won't hear from us again.</p>")
    return HTMLResponse(
        f"<html><body><h1>Unsubscribe from future emails about {lead.name}</h1>"
        f"<p>Click to stop all future messages.</p>"
        f'<a style="padding:10px 18px;background:#c00;color:#fff;text-decoration:none" '
        f'href="/u?l={lead.id}&m={msg.id}&t={t}&confirm=1">Unsubscribe</a></body></html>'
    )
