import re
import hashlib
import hmac
import math
from datetime import timedelta
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import LoginFailure, User, utcnow

bp = Blueprint("auth", __name__)
LOGIN_FAILURE_LIMIT = 5
LOGIN_WINDOW = timedelta(minutes=15)


def login_digest(email):
    return hmac.new(current_app.secret_key.encode(), email.encode(), hashlib.sha256).hexdigest()


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("tickets.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or len(name) > 100 or len(email) > 255 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(password) < 12:
            flash("Enter a name, valid email, and password of at least 12 characters.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("This email is already registered.", "danger")
        else:
            user = User(name=name, email=email, role="user")
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("This email is already registered.", "danger")
            else:
                login_user(user)
                return redirect(url_for("tickets.dashboard"))
    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("tickets.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        digest = login_digest(email)
        now = utcnow()
        recent = LoginFailure.query.filter(
            LoginFailure.email_digest == digest,
            LoginFailure.created_at > now - LOGIN_WINDOW,
        )
        if recent.count() >= LOGIN_FAILURE_LIMIT:
            earliest = recent.order_by(LoginFailure.created_at.asc()).first()
            retry_after = max(1, math.ceil((earliest.created_at + LOGIN_WINDOW - now).total_seconds()))
            flash("Too many login attempts. Try again in 15 minutes.", "danger")
            response = current_app.make_response((render_template("auth/login.html"), 429))
            response.headers["Retry-After"] = str(retry_after)
            return response
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form.get("password", "")):
            target = request.args.get("next", "")
            if target and (not target.startswith("/") or target.startswith("//") or "\\" in target or urlsplit(target).scheme or urlsplit(target).netloc):
                abort(400)
            LoginFailure.query.filter_by(email_digest=digest).delete()
            db.session.commit()
            login_user(user)
            return redirect(target or url_for("tickets.dashboard"))
        LoginFailure.query.filter(LoginFailure.created_at < now - timedelta(days=1)).delete()
        db.session.add(LoginFailure(email_digest=digest, created_at=now))
        db.session.commit()
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
