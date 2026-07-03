"""Platform notification config, Teams webhooks, digest schedule.

Revision ID: 0011_platform_teams_digest_notifications
Revises: 0010_roadmap_metrics
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0011_platform_teams_digest_notifications"
down_revision = "0010_roadmap_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if not insp.has_table("platform_notification_configs"):
        op.create_table(
            "platform_notification_configs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("smtp_host", sa.String(length=255), nullable=True),
            sa.Column("smtp_port", sa.Integer(), nullable=True),
            sa.Column("smtp_username", sa.String(length=255), nullable=True),
            sa.Column("smtp_password_encrypted", sa.Text(), nullable=True),
            sa.Column("smtp_from_email", sa.String(length=255), nullable=True),
            sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("use_ssl", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("allow_tenant_smtp_override", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("templates_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("slack_incoming_webhook_encrypted", sa.Text(), nullable=True),
            sa.Column("teams_incoming_webhook_encrypted", sa.Text(), nullable=True),
            sa.Column("last_test_ok", sa.Boolean(), nullable=True),
            sa.Column("last_test_error", sa.Text(), nullable=True),
            sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if insp.has_table("tenant_notification_configs"):
        cols = {c["name"] for c in insp.get_columns("tenant_notification_configs")}
        if "teams_incoming_webhook_encrypted" not in cols:
            op.add_column(
                "tenant_notification_configs",
                sa.Column("teams_incoming_webhook_encrypted", sa.Text(), nullable=True),
            )
        if "notification_channels_json" not in cols:
            op.add_column(
                "tenant_notification_configs",
                sa.Column(
                    "notification_channels_json",
                    sa.JSON(),
                    nullable=False,
                    server_default=sa.text("'{}'"),
                ),
            )
        if "digest_schedule_json" not in cols:
            op.add_column(
                "tenant_notification_configs",
                sa.Column(
                    "digest_schedule_json",
                    sa.JSON(),
                    nullable=False,
                    server_default=sa.text("'{}'"),
                ),
            )


def downgrade() -> None:
    op.drop_column("tenant_notification_configs", "digest_schedule_json")
    op.drop_column("tenant_notification_configs", "notification_channels_json")
    op.drop_column("tenant_notification_configs", "teams_incoming_webhook_encrypted")
    op.drop_table("platform_notification_configs")
