"""governance share links: slack webhook + digest emails on tenant notifications

Revision ID: 0007_governance_share_notifications
Revises: 0006_portfolio_project_links
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0007_governance_share_notifications"
down_revision = "0006_portfolio_project_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("tenant_notification_configs"):
        op.create_table(
            "tenant_notification_configs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
            sa.Column("smtp_host", sa.String(length=255), nullable=True),
            sa.Column("smtp_port", sa.Integer(), nullable=True),
            sa.Column("smtp_username", sa.String(length=255), nullable=True),
            sa.Column("smtp_password_encrypted", sa.Text(), nullable=True),
            sa.Column("smtp_from_email", sa.String(length=255), nullable=True),
            sa.Column("use_tls", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("use_ssl", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("templates_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("slack_incoming_webhook_encrypted", sa.Text(), nullable=True),
            sa.Column(
                "governance_notify_on_run_complete",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "governance_run_notify_emails_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
            sa.Column("last_test_ok", sa.Boolean(), nullable=True),
            sa.Column("last_test_error", sa.Text(), nullable=True),
            sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index(
            "ix_tenant_notification_configs_tenant_id",
            "tenant_notification_configs",
            ["tenant_id"],
            unique=True,
        )
        return

    cols = {c["name"] for c in insp.get_columns("tenant_notification_configs")}
    if "slack_incoming_webhook_encrypted" not in cols:
        op.add_column(
            "tenant_notification_configs",
            sa.Column("slack_incoming_webhook_encrypted", sa.Text(), nullable=True),
        )
    if "governance_notify_on_run_complete" not in cols:
        op.add_column(
            "tenant_notification_configs",
            sa.Column(
                "governance_notify_on_run_complete",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "governance_run_notify_emails_json" not in cols:
        op.add_column(
            "tenant_notification_configs",
            sa.Column(
                "governance_run_notify_emails_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
        )


def downgrade() -> None:
    op.drop_column("tenant_notification_configs", "governance_run_notify_emails_json")
    op.drop_column("tenant_notification_configs", "governance_notify_on_run_complete")
    op.drop_column("tenant_notification_configs", "slack_incoming_webhook_encrypted")
