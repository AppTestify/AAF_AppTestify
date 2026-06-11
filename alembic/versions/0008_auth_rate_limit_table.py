"""add auth rate limit table

Revision ID: dd49746e1ddd
Revises: 0007_governance_share_notifications
Create Date: 2026-06-10 13:44:00.877613
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "dd49746e1ddd"
down_revision = "0007_governance_share_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_rate_limits",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_attempt_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("email"),
    )


def downgrade() -> None:
    op.drop_table("auth_rate_limits")
