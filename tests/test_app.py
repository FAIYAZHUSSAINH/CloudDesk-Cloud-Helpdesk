from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.extensions import db
from app.models import LoginFailure, Ticket, TicketActivity, User
from app.services import admin_stats, local_time, sla_info
from conftest import login, ticket, token


def test_registration_and_duplicate(client, app):
    invalid = client.post("/register", data={"name": "New Student", "email": "bad@", "password": "a-long-password", "csrf_token": token(client, "/register")})
    assert b"valid email" in invalid.data
    response = client.post("/register", data={"name": "New Student", "email": "new@example.test", "password": "a-long-password", "role": "admin", "csrf_token": token(client, "/register")})
    assert response.status_code == 302
    with app.app_context():
        assert User.query.filter_by(email="new@example.test").one().role == "user"
    client.post("/logout", data={"csrf_token": token(client, "/tickets")})
    duplicate = client.post("/register", data={"name": "New Student", "email": "new@example.test", "password": "a-long-password", "csrf_token": token(client, "/register")}, follow_redirects=True)
    assert b"already registered" in duplicate.data
    with app.app_context():
        assert User.query.filter_by(email="new@example.test").count() == 1


def test_login_and_authentication(client, users):
    assert client.get("/tickets").status_code == 302
    assert client.get("/api/tickets").status_code == 401
    bad = login(client, password="incorrect")
    assert b"Invalid email or password" in bad.data
    assert login(client).status_code == 302
    assert client.get("/tickets").status_code == 200
    assert client.post("/logout", data={"csrf_token": token(client, "/tickets")}).status_code == 302
    assert client.get("/api/tickets").status_code == 401


def test_login_rejects_external_next_before_session_creation(client, users):
    for target in ("//evil.example", "javascript:alert(1)", "/\\evil.example"):
        response = client.post(f"/login?next={target}", data={"email": "alice@example.test", "password": "a-long-password", "csrf_token": token(client)})
        assert response.status_code == 400
        assert client.get("/api/tickets").status_code == 401


def test_ticket_validation_persistence_and_access(client, app, users):
    login(client)
    csrf = token(client, "/tickets/new")
    assert client.post("/tickets/new", data={"title": "", "description": "Issue", "category": "Network", "priority": "High", "csrf_token": csrf}).status_code == 200
    assert client.post("/tickets/new", data={"title": "Issue", "description": "Issue", "category": "Network", "priority": "Critical", "csrf_token": csrf}).status_code == 200
    response = client.post("/tickets/new", data={"title": "Wi-Fi not working in Lab 301", "description": "No connectivity", "category": "Network", "priority": "High", "status": "Resolved", "user_id": users["bob@example.test"], "csrf_token": csrf})
    assert response.status_code == 302
    with app.app_context():
        record = Ticket.query.one()
        assert record.user_id == users["alice@example.test"]
        assert record.status == "Open"
        record_id = record.id
    assert b"Wi-Fi not working in Lab 301" in client.get("/tickets").data
    assert client.get(f"/tickets/{record_id}").status_code == 200
    second = ticket(app, users["bob@example.test"])
    assert client.get(f"/tickets/{second}").status_code == 403
    assert client.post(f"/tickets/{second}/description", data={"description": "hacked", "csrf_token": token(client, f"/tickets/{record_id}")}).status_code == 403
    assert client.get("/admin/").status_code == 403
    assert client.post(f"/admin/tickets/{record_id}/status", data={"status": "Resolved", "csrf_token": token(client, f"/tickets/{record_id}")}).status_code == 403


def test_admin_status_activity_and_reopen(client, app, users):
    record_id = ticket(app, users["alice@example.test"])
    login(client, "admin@example.test")
    assert b"Support dashboard" in client.get("/admin/").data
    csrf = token(client, f"/tickets/{record_id}")
    assert client.post(f"/admin/tickets/{record_id}/status", data={"status": "In Progress", "csrf_token": csrf}).status_code == 302
    assert client.post(f"/admin/tickets/{record_id}/status", data={"status": "Resolved", "csrf_token": csrf}).status_code == 302
    with app.app_context():
        record = db.session.get(Ticket, record_id)
        assert record.resolved_at and record.resolved_at.tzinfo
        assert TicketActivity.query.filter_by(ticket_id=record_id).count() == 2
    assert client.post(f"/admin/tickets/{record_id}/status", data={"status": "Open", "csrf_token": csrf}).status_code == 302
    with app.app_context():
        record = db.session.get(Ticket, record_id)
        assert record.resolved_at is None
        assert TicketActivity.query.filter_by(ticket_id=record_id).order_by(TicketActivity.id.desc()).first().action == "reopened"


def test_sla_and_timezone(app, users):
    with app.app_context():
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        record = Ticket(user_id=users["alice@example.test"], title="SLA test", description="Test", category="Network", priority="High", status="Open", created_at=start, updated_at=start)
        db.session.add(record)
        db.session.commit()
        db.session.refresh(record)
        assert record.created_at.tzinfo == timezone.utc
        assert "05:30 AM IST" in local_time(record.created_at)
        assert sla_info(record, start + timedelta(hours=1))["label"] == "Time remaining"
        assert sla_info(record, start + timedelta(hours=3))["label"] == "Overdue"
        record.status = "Resolved"
        record.resolved_at = start + timedelta(hours=1)
        db.session.commit()
        assert sla_info(record)["label"] == "SLA Met"
        record.resolved_at = start + timedelta(hours=3)
        db.session.commit()
        assert sla_info(record)["label"] == "SLA Breached"


def test_api_auth_validation_csrf_and_stats(client, app, users):
    assert client.get("/api/health").json == {"status": "ok"}
    login(client)
    payload = {"title": "Broken Wi-Fi", "description": "No network", "category": "Network", "priority": "High", "status": "Resolved", "user_id": users["bob@example.test"]}
    assert client.post("/api/tickets", json=payload).status_code == 400
    csrf = token(client, "/tickets/new")
    headers = {"X-CSRFToken": csrf}
    assert client.post("/api/tickets", json={**payload, "priority": "Critical"}, headers=headers).status_code == 400
    response = client.post("/api/tickets", json=payload, headers=headers)
    assert response.status_code == 201
    record_id = response.json["ticket"]["id"]
    assert response.json["ticket"]["status"] == "Open"
    assert response.json["ticket"]["user_id"] == users["alice@example.test"]
    assert len(client.get("/api/tickets").json["tickets"]) == 1
    assert client.get("/api/dashboard/stats").json["stats"]["Open"] == 1
    assert client.patch(f"/api/tickets/{record_id}", json={"status": "Resolved"}, headers=headers).status_code == 403
    assert client.patch(f"/api/tickets/{record_id}", json={"description": "Changed"}, headers=headers).status_code == 200
    assert client.get("/api/tickets/99999").status_code == 404
    bob_id = ticket(app, users["bob@example.test"])
    assert client.get(f"/api/tickets/{bob_id}").status_code == 403
    assert client.patch(f"/api/tickets/{bob_id}", json={"description": "Changed"}, headers=headers).status_code == 403
    with app.app_context():
        assert db.session.get(Ticket, record_id).description == "Changed"
    client.post("/logout", data={"csrf_token": csrf})
    login(client, "admin@example.test")
    admin_headers = {"X-CSRFToken": token(client, "/tickets")}
    resolved = client.patch(f"/api/tickets/{record_id}", json={"status": "Resolved"}, headers=admin_headers)
    assert resolved.status_code == 200
    assert resolved.json["ticket"]["resolved_at"] is not None
    assert client.get("/api/dashboard/stats").json["stats"]["Resolved"] == 1


def test_migration_foreign_keys_and_seed(client, app, users):
    with app.app_context():
        assert db.session.execute(text("SELECT version_num FROM alembic_version")).scalar() == "bb7aa36d7612"
        record_id = ticket(app, users["alice@example.test"])
        assert db.session.get(Ticket, record_id).creator.email == "alice@example.test"
        db.session.add(Ticket(user_id=99999, title="Orphan", description="Invalid", category="Other", priority="Low", status="Open"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-demo", "--user-password", "demo-password-one", "--admin-password", "demo-password-two"])
    assert result.exit_code == 0, result.output
    again = runner.invoke(args=["seed-demo", "--user-password", "demo-password-one", "--admin-password", "demo-password-two"])
    assert again.exit_code == 0
    with app.app_context():
        assert Ticket.query.count() == 5
        assert User.query.filter_by(email="admin@example.test").one().role == "admin"
        assert admin_stats()["SLA Breaches"] == 2


def test_cli_admin_provisioning(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-admin", "--name", "Support Lead", "--email", "lead@example.test", "--password", "a-strong-admin-password"])
    assert result.exit_code == 0, result.output
    with app.app_context():
        assert User.query.filter_by(email="lead@example.test").one().is_admin
    duplicate = runner.invoke(args=["create-admin", "--name", "Support Lead", "--email", "lead@example.test", "--password", "a-strong-admin-password"])
    assert duplicate.exit_code != 0


def test_login_failure_limit_is_shared_and_expires(app, client, users):
    for _ in range(5):
        assert login(client, password="incorrect").status_code == 200
    with app.app_context():
        failures = LoginFailure.query.all()
        assert len(failures) == 5
        assert all("alice" not in item.email_digest for item in failures)
    other_worker = app.test_client()
    with app.app_context():
        blocked = login(other_worker)
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
    assert b"Too many login attempts" in blocked.data
    with app.app_context():
        for item in LoginFailure.query.all():
            item.created_at -= timedelta(minutes=16)
        db.session.commit()
    with app.app_context():
        assert login(other_worker).status_code == 302
    with app.app_context():
        assert LoginFailure.query.count() == 0


def test_render_requires_database_secret_and_trusted_host(monkeypatch):
    from app import create_app

    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "clouddesk.onrender.com")
    config = {"SECRET_KEY": "x" * 32, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"}
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        create_app(config)
    config["SQLALCHEMY_DATABASE_URI"] = "postgresql+psycopg://user:pass@localhost/db"
    with pytest.raises(RuntimeError, match="sslmode"):
        create_app(config)
    config["SQLALCHEMY_DATABASE_URI"] += "?sslmode=require"
    config["SECRET_KEY"] = "too-short"
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config)
    config["SECRET_KEY"] = "replace-with-a-long-random-secret"
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app(config)
    config["SECRET_KEY"] = "x" * 32
    application = create_app(config)
    assert application.config["SESSION_COOKIE_SECURE"]
    assert application.config["TRUSTED_HOSTS"] == ["clouddesk.onrender.com"]
    assert application.test_client().get("/api/health", base_url="https://evil.example").status_code == 400
    healthy = application.test_client().get("/api/health", base_url="https://clouddesk.onrender.com")
    assert healthy.status_code == 200
    assert healthy.headers["Strict-Transport-Security"]
