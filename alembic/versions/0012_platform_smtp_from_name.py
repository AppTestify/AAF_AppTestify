"""Add smtp_from_name to platform_notification_configs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0012_platform_smtp_from_name"
down_revision = "0011_platform_teams_digest_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("platform_notification_configs"):
        return
    cols = {c["name"] for c in insp.get_columns("platform_notification_configs")}
    if "smtp_from_name" not in cols:
        op.add_column("platform_notification_configs", sa.Column("smtp_from_name", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("platform_notification_configs", "smtp_from_name")
