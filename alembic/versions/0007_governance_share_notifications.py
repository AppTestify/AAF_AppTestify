"""governance share links: slack webhook + digest emails on tenant notifications

Revision ID: 0007_governance_share_notifications
Revises: 0006_portfolio_project_links
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_governance_share_notifications"
down_revision = "0006_portfolio_project_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_notification_configs",
        sa.Column("slack_incoming_webhook_encrypted", sa.Text(), nullable=True),
    )
    op.add_column(
        "tenant_notification_configs",
        sa.Column(
            "governance_notify_on_run_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
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
