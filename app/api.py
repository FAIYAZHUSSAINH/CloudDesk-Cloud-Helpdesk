from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from .extensions import db
from .models import Ticket, utcnow
from .services import CATEGORIES, PRIORITIES, STATUSES, admin_stats, counts, sla_info, update_status

bp = Blueprint("api", __name__, url_prefix="/api")


def require_user():
    if not current_user.is_authenticated:
        abort(401)


def ticket_json(ticket):
    return {"id": ticket.id, "title": ticket.title, "description": ticket.description, "category": ticket.category, "priority": ticket.priority, "status": ticket.status, "user_id": ticket.user_id, "created_at": ticket.created_at.isoformat(), "updated_at": ticket.updated_at.isoformat(), "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None, "sla": sla_info(ticket)["label"]}


def find_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        abort(404)
    if not current_user.is_admin and ticket.user_id != current_user.id:
        abort(403)
    return ticket


@bp.get("/health")
def health():
    return jsonify(status="ok")


@bp.get("/tickets")
def list_tickets():
    require_user()
    query = Ticket.query if current_user.is_admin else Ticket.query.filter_by(user_id=current_user.id)
    return jsonify(tickets=[ticket_json(t) for t in query.order_by(Ticket.created_at.desc()).all()])


@bp.post("/tickets")
def create_ticket():
    require_user()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Expected JSON object"), 400
    title = data.get("title", "")
    description = data.get("description", "")
    if not isinstance(title, str) or not isinstance(description, str) or not title.strip() or len(title.strip()) > 150 or not description.strip() or len(description.strip()) > 10000 or data.get("category") not in CATEGORIES or data.get("priority") not in PRIORITIES:
        return jsonify(error="Invalid ticket fields"), 400
    ticket = Ticket(creator=current_user, title=title.strip(), description=description.strip(), category=data["category"], priority=data["priority"], status="Open")
    db.session.add(ticket)
    db.session.commit()
    return jsonify(ticket=ticket_json(ticket)), 201


@bp.get("/tickets/<int:ticket_id>")
def get_ticket(ticket_id):
    require_user()
    return jsonify(ticket=ticket_json(find_ticket(ticket_id)))


@bp.patch("/tickets/<int:ticket_id>")
def patch_ticket(ticket_id):
    require_user()
    ticket = find_ticket(ticket_id)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not data or set(data) - {"description", "status"}:
        return jsonify(error="Only description and status may be updated"), 400
    if "status" in data:
        if not current_user.is_admin:
            abort(403)
        if data["status"] not in STATUSES:
            return jsonify(error="Invalid status"), 400
        update_status(ticket, data["status"], current_user)
    if "description" in data:
        if ticket.user_id != current_user.id or ticket.status == "Resolved":
            abort(403)
        description = data["description"]
        if not isinstance(description, str) or not description.strip() or len(description.strip()) > 10000:
            return jsonify(error="Invalid description"), 400
        ticket.description = description.strip()
        ticket.updated_at = utcnow()
    db.session.commit()
    return jsonify(ticket=ticket_json(ticket))


@bp.get("/dashboard/stats")
def dashboard_stats():
    require_user()
    return jsonify(stats=admin_stats() if current_user.is_admin else counts(Ticket.query.filter_by(user_id=current_user.id)))
