"""add access leads table

Revision ID: 0005_access_leads
Revises: 0004_rar_and_workflow_runs
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0005_access_leads"
down_revision = "0004_rar_and_workflow_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "access_leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("work_email", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("converted_tenant_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_leads_work_email", "access_leads", ["work_email"])
    op.create_index("ix_access_leads_status", "access_leads", ["status"])
    op.create_index("ix_access_leads_converted_tenant_id", "access_leads", ["converted_tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_access_leads_converted_tenant_id", table_name="access_leads")
    op.drop_index("ix_access_leads_status", table_name="access_leads")
    op.drop_index("ix_access_leads_work_email", table_name="access_leads")
    op.drop_table("access_leads")
