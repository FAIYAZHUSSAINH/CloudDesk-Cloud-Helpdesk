from datetime import timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func

from .extensions import db
from .models import Ticket, TicketActivity, utcnow

CATEGORIES = ("Network", "Hardware", "Software", "Account", "Other")
PRIORITIES = ("Low", "Medium", "High")
STATUSES = ("Open", "In Progress", "Resolved")
SLA_HOURS = {"High": 2, "Medium": 8, "Low": 24}
KOLKATA = ZoneInfo("Asia/Kolkata")


def local_time(value):
    return value.astimezone(KOLKATA).strftime("%d %b %Y, %I:%M %p IST") if value else "—"


def sla_info(ticket, now=None):
    now = now or utcnow()
    deadline = ticket.created_at + timedelta(hours=SLA_HOURS[ticket.priority])
    if ticket.status == "Resolved" and ticket.resolved_at:
        elapsed = ticket.resolved_at - ticket.created_at
        return {"label": "SLA Met" if ticket.resolved_at <= deadline else "SLA Breached", "seconds": elapsed.total_seconds(), "deadline": deadline}
    remaining = deadline - now
    return {"label": "Time remaining" if remaining.total_seconds() >= 0 else "Overdue", "seconds": abs(remaining.total_seconds()), "deadline": deadline}


def update_status(ticket, status, actor):
    if status not in STATUSES:
        raise ValueError("Invalid status")
    if ticket.status == status:
        return False
    old = ticket.status
    ticket.status = status
    ticket.resolved_at = utcnow() if status == "Resolved" else None
    ticket.updated_at = utcnow()
    action = "resolved" if status == "Resolved" else "reopened" if old == "Resolved" else "status_changed"
    db.session.add(TicketActivity(ticket=ticket, actor=actor, action=action, old_status=old, new_status=status))
    return True


def counts(query):
    rows = query.with_entities(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status).all()
    result = {status: 0 for status in STATUSES}
    result.update(rows)
    result["Total"] = sum(result.values())
    return result


def distribution(column):
    return dict(db.session.query(column, func.count(Ticket.id)).group_by(column).all())


def admin_stats():
    summary = counts(Ticket.query)
    unresolved = Ticket.query.filter(Ticket.status != "Resolved", Ticket.created_at < utcnow() - timedelta(hours=2)).all()
    resolved_breaches = Ticket.query.filter(Ticket.status == "Resolved", Ticket.resolved_at.isnot(None)).all()
    summary["SLA Breaches"] = sum(sla_info(t)["label"] == "Overdue" for t in unresolved) + sum(sla_info(t)["label"] == "SLA Breached" for t in resolved_breaches)
    return summary
