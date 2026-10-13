import re

import pytest
from flask_migrate import upgrade

from app import create_app
from app.extensions import db
from app.models import Ticket, User


@pytest.fixture
def app(tmp_path):
    application = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(tmp_path / 'test.db').as_posix()}", "WTF_CSRF_ENABLED": True})
    with application.app_context():
        upgrade()
        yield application
        db.session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def users(app):
    with app.app_context():
        for name, email, role in (("Alice", "alice@example.test", "user"), ("Bob", "bob@example.test", "user"), ("Admin", "admin@example.test", "admin")):
            user = User(name=name, email=email, role=role)
            user.set_password("a-long-password")
            db.session.add(user)
        db.session.commit()
        return {u.email: u.id for u in User.query.all()}


def token(client, path="/login"):
    page = client.get(path)
    assert page.status_code == 200
    match = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
    assert match
    return match.group(1).decode()


def login(client, email="alice@example.test", password="a-long-password"):
    return client.post("/login", data={"email": email, "password": password, "csrf_token": token(client)})


def ticket(app, user_id, **kwargs):
    with app.app_context():
        record = Ticket(user_id=user_id, title=kwargs.get("title", "Broken Wi-Fi"), description="No connection", category="Network", priority=kwargs.get("priority", "High"), status="Open")
        db.session.add(record)
        db.session.commit()
        return record.id
