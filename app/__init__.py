import logging
import os
from datetime import timedelta

import click
from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFError
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from .config import Config
from .extensions import csrf, db, login_manager, migrate
from .models import Ticket, TicketActivity, User, utcnow
from .services import local_time, sla_info


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        if app.config.get("TESTING"):
            app.config["SECRET_KEY"] = "test-only-key"
        else:
            raise RuntimeError("SECRET_KEY must be set in the environment")
    if os.getenv("RENDER", "").lower() == "true" and not app.config.get("TESTING"):
        if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql+psycopg://"):
            raise RuntimeError("Render requires a PostgreSQL DATABASE_URL")
        if make_url(app.config["SQLALCHEMY_DATABASE_URI"]).query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
            raise RuntimeError("Render requires a PostgreSQL DATABASE_URL with sslmode=require or stronger")
        if len(app.config["SECRET_KEY"]) < 32 or app.config["SECRET_KEY"] == "replace-with-a-long-random-secret":
            raise RuntimeError("Render requires a unique SECRET_KEY of at least 32 characters")
        hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
        if not hostname:
            raise RuntimeError("Render requires RENDER_EXTERNAL_HOSTNAME")
        app.config["TRUSTED_HOSTS"] = [hostname, *[host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]]
        app.config["SESSION_COOKIE_SECURE"] = True
    db.init_app(app)
    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            @event.listens_for(db.engine, "connect")
            def enable_sqlite_foreign_keys(connection, connection_record):
                cursor = connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .auth import bp as auth_bp
    from .tickets import bp as tickets_bp
    from .admin import bp as admin_bp
    from .api import bp as api_bp

    for bp in (auth_bp, tickets_bp, admin_bp, api_bp):
        app.register_blueprint(bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id)) if user_id.isdigit() else None

    @app.template_filter("localtime")
    def localtime_filter(value):
        return local_time(value)

    @app.context_processor
    def template_helpers():
        return {"sla_info": sla_info}

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error="CSRF token missing or invalid"), 400
        return render_template("errors/error.html", code=400, message="Your form expired. Reload the page and try again."), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description), error.code
        return render_template("errors/error.html", code=error.code, message=error.description), error.code

    @app.errorhandler(Exception)
    def internal_error(error):
        if app.config.get("TESTING"):
            raise error
        if isinstance(error, SQLAlchemyError):
            db.session.rollback()
        app.logger.exception("Request failed: %s %s", request.method, request.path)
        if request.path.startswith("/api/"):
            return jsonify(error="Internal server error"), 500
        return render_template("errors/error.html", code=500, message="Something went wrong. Please try again."), 500

    logging.basicConfig(level=logging.INFO)

    @app.after_request
    def log_request(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        app.logger.info("%s %s %s", request.method, request.path, response.status_code)
        return response

    register_commands(app)
    return app


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        email = email.strip().lower()
        if len(password) < 12:
            raise click.ClickException("Use a password of at least 12 characters")
        if User.query.filter_by(email=email).first():
            raise click.ClickException("Email already exists")
        user = User(name=name.strip(), email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("Admin created")

    @app.cli.command("seed-demo")
    @click.option("--user-password", envvar="DEMO_USER_PASSWORD", required=True, hide_input=True)
    @click.option("--admin-password", envvar="DEMO_ADMIN_PASSWORD", required=True, hide_input=True)
    def seed_demo(user_password, admin_password):
        if min(len(user_password), len(admin_password)) < 12:
            raise click.ClickException("Both demo passwords must have at least 12 characters")
        users = {}
        for name, email, role, password in (
            ("Aarav Student", "aarav@example.test", "user", user_password),
            ("Mira Student", "mira@example.test", "user", user_password),
            ("IT Admin", "admin@example.test", "admin", admin_password),
        ):
            user = User.query.filter_by(email=email).first()
            if user and user.role != role:
                raise click.ClickException(f"Existing demo email {email} has a different role")
            if not user:
                user = User(name=name, email=email, role=role)
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
            users[email] = user
        examples = [
            ("Wi-Fi intermittent in Lab 301", "Network", "High", "Open", 1, None),
            ("ERP login fails", "Account", "Medium", "In Progress", 10, None),
            ("Install Python on lab PC", "Software", "Low", "Resolved", 30, 2),
            ("Laptop display flickers", "Hardware", "High", "Resolved", 6, 3),
        ]
        for title, category, priority, status, age_hours, resolve_after in examples:
            if Ticket.query.filter_by(title=title, user_id=users["aarav@example.test"].id).first():
                continue
            created = utcnow() - timedelta(hours=age_hours)
            ticket = Ticket(title=title, description=f"Demo issue: {title}.", category=category, priority=priority, status=status, creator=users["aarav@example.test"], created_at=created, updated_at=created, resolved_at=created + timedelta(hours=resolve_after) if resolve_after else None)
            db.session.add(ticket)
            if status == "Resolved":
                db.session.flush()
                db.session.add(TicketActivity(ticket=ticket, actor=users["admin@example.test"], action="resolved", old_status="Open", new_status="Resolved", created_at=ticket.resolved_at))
        db.session.commit()
        click.echo("Demo data ready; existing accounts and tickets were kept")
