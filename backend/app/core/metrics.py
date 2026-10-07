from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.settings_service import get_setting
from app.models.call import Call
from app.models.lead import Lead
from app.models.message import Message
from app.models.demo_site import DemoSite


def _day_bucket(dt: datetime) -> date:
    return dt.date() if dt else None


def overview_metrics(db: Session) -> dict:
    leads_found = db.query(Lead).count()
    with_contact = db.query(Lead).filter(Lead.contact_type.isnot(None)).count() or db.query(Lead).join(Lead.contacts).count()
    demos_built = db.query(DemoSite).count()
    emails_drafted = db.query(Message).filter(Message.channel == 'email', Message.status.in_(['draft', 'queued', 'approved'])).count()
    emails_sent = db.query(Message).filter(Message.status == 'sent').count()
    replies = db.query(Message).filter(Message.status == 'replied').count() or db.query(Message).filter(Message.direction == 'inbound').count()
    opted_out = db.query(Message).filter(Message.status == 'opted_out').count()
    calls_made = db.query(Call).count()

    total = int(get_setting(db, 'stats.total_messages', 0) or 0)
    bounces = int(get_setting(db, 'stats.bounces', 0) or 0)
    bounce_rate = round(bounces / max(total, 1), 4)
    complaint_rate = float(get_setting(db, 'stats.complaint_rate', 0.0) or 0.0)

    # funnel: discovered -> with_contact -> profiled -> demo -> drafted -> sent -> replied
    profiled = db.query(Lead).join(Lead.profile).count()
    funnel = {
        'discovered': leads_found,
        'with_contact': with_contact,
        'profiled': profiled,
        'demo_built': demos_built,
        'emails_drafted': emails_drafted,
        'emails_sent': emails_sent,
        'replied': replies,
    }

    # leads per day (last 14 days, from created_at)
    since = datetime.now() - timedelta(days=13)
    rows = db.query(
        func.date(Lead.created_at).label('d'), func.count(Lead.id).label('c'),
    ).filter(Lead.created_at >= since).group_by('d').all()
    by_day = {str(r.d): r.c for r in rows}
    leads_per_day = []
    for i in range(-13, 1):
        d = (datetime.now() + timedelta(days=i)).date()
        leads_per_day.append({'date': str(d), 'count': by_day.get(str(d), 0)})

    return {
        'kpis': {
            'leads_found': leads_found,
            'with_contact': with_contact,
            'demos_built': demos_built,
            'emails_drafted': emails_drafted,
            'emails_sent': emails_sent,
            'replies': replies,
            'bounce_rate': bounce_rate,
            'complaint_rate': complaint_rate,
            'calls_made': calls_made,
            'opted_out': opted_out,
        },
        'funnel': funnel,
        'leads_per_day': leads_per_day,
    }