from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import Ticket, TicketActivity
from .services import STATUSES, admin_stats, distribution, update_status

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@bp.get("/")
@admin_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        stats=admin_stats(),
        charts={"status": distribution(Ticket.status), "priority": distribution(Ticket.priority), "category": distribution(Ticket.category)},
        activities=TicketActivity.query.order_by(TicketActivity.created_at.desc()).limit(8).all(),
    )


@bp.post("/tickets/<int:ticket_id>/status")
@admin_required
def set_status(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        abort(404)
    status = request.form.get("status", "")
    if status not in STATUSES:
        abort(400)
    if update_status(ticket, status, current_user):
        db.session.commit()
        flash("Ticket status updated.", "success")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))
