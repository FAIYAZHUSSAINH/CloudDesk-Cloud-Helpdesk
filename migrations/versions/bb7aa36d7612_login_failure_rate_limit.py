"""Store failed login attempts for a shared, persistent rate limit.

Revision ID: bb7aa36d7612
Revises: 9c460ec6c092
"""

from alembic import op
import sqlalchemy as sa

from app.models import UTCDateTime


revision = "bb7aa36d7612"
down_revision = "9c460ec6c092"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_failures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
    )
    op.create_index("ix_login_failures_email_created", "login_failures", ["email_digest", "created_at"])
    op.create_index("ix_login_failures_created", "login_failures", ["created_at"])


def downgrade():
    op.drop_index("ix_login_failures_created", table_name="login_failures")
    op.drop_index("ix_login_failures_email_created", table_name="login_failures")
    op.drop_table("login_failures")
