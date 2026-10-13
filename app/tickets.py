from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import Ticket, utcnow
from .services import CATEGORIES, PRIORITIES, STATUSES, counts

bp = Blueprint("tickets", __name__)


def owned_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        abort(404)
    if not current_user.is_admin and ticket.user_id != current_user.id:
        abort(403)
    return ticket


@bp.get("/")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin.dashboard"))
    query = Ticket.query.filter_by(user_id=current_user.id)
    return render_template("tickets/dashboard.html", stats=counts(query), tickets=query.order_by(Ticket.created_at.desc()).limit(5).all())


@bp.route("/tickets/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "")
        priority = request.form.get("priority", "")
        if not title or len(title) > 150 or not description or len(description) > 10000 or category not in CATEGORIES or priority not in PRIORITIES:
            flash("Complete all fields with a valid category and priority.", "danger")
        else:
            ticket = Ticket(creator=current_user, title=title, description=description, category=category, priority=priority, status="Open")
            db.session.add(ticket)
            db.session.commit()
            flash(f"Ticket #{ticket.id} created.", "success")
            return redirect(url_for("tickets.detail", ticket_id=ticket.id))
    return render_template("tickets/form.html", categories=CATEGORIES, priorities=PRIORITIES)


@bp.get("/tickets")
@login_required
def index():
    query = Ticket.query if current_user.is_admin else Ticket.query.filter_by(user_id=current_user.id)
    for field, choices in (("status", STATUSES), ("priority", PRIORITIES), ("category", CATEGORIES)):
        value = request.args.get(field, "")
        if value:
            if value not in choices:
                abort(400)
            query = query.filter(getattr(Ticket, field) == value)
    return render_template("tickets/index.html", tickets=query.order_by(Ticket.created_at.desc()).all(), statuses=STATUSES, priorities=PRIORITIES, categories=CATEGORIES)


@bp.get("/tickets/<int:ticket_id>")
@login_required
def detail(ticket_id):
    return render_template("tickets/detail.html", ticket=owned_ticket(ticket_id), statuses=STATUSES)


@bp.post("/tickets/<int:ticket_id>/description")
@login_required
def edit_description(ticket_id):
    ticket = owned_ticket(ticket_id)
    if ticket.user_id != current_user.id or ticket.status == "Resolved":
        abort(403)
    description = request.form.get("description", "").strip()
    if not description or len(description) > 10000:
        flash("Description must be between 1 and 10,000 characters.", "danger")
    else:
        ticket.description = description
        ticket.updated_at = utcnow()
        db.session.commit()
        flash("Description updated.", "success")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))
