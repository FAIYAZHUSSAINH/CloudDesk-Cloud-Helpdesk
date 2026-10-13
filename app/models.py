from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, Index, TypeDecorator
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """SQLite drops timezone data; keep one UTC contract on both databases."""

    impl = db.DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    created_at = db.Column(UTCDateTime, nullable=False, default=utcnow)
    tickets = db.relationship("Ticket", back_populates="creator", lazy="select")
    __table_args__ = (CheckConstraint("role IN ('user', 'admin')", name="valid_user_role"),)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"


class Ticket(db.Model):
    __tablename__ = "tickets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(20), nullable=False)
    priority = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Open")
    created_at = db.Column(UTCDateTime, nullable=False, default=utcnow)
    updated_at = db.Column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)
    resolved_at = db.Column(UTCDateTime)
    creator = db.relationship("User", back_populates="tickets")
    activities = db.relationship("TicketActivity", back_populates="ticket", order_by="TicketActivity.created_at", cascade="all, delete-orphan")
    __table_args__ = (
        CheckConstraint("category IN ('Network','Hardware','Software','Account','Other')", name="valid_category"),
        CheckConstraint("priority IN ('Low','Medium','High')", name="valid_priority"),
        CheckConstraint("status IN ('Open','In Progress','Resolved')", name="valid_status"),
        Index("ix_tickets_status_priority", "status", "priority"),
    )


class TicketActivity(db.Model):
    __tablename__ = "ticket_activities"
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id"), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(30), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(UTCDateTime, nullable=False, default=utcnow)
    ticket = db.relationship("Ticket", back_populates="activities")
    actor = db.relationship("User")


class LoginFailure(db.Model):
    __tablename__ = "login_failures"
    id = db.Column(db.Integer, primary_key=True)
    email_digest = db.Column(db.String(64), nullable=False)
    created_at = db.Column(UTCDateTime, nullable=False, default=utcnow)
    __table_args__ = (
        Index("ix_login_failures_email_created", "email_digest", "created_at"),
        Index("ix_login_failures_created", "created_at"),
    )
