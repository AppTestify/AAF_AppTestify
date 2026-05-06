"""add agentic intelligence tables

Revision ID: 0003_agentic_intelligence_v1
Revises: 0002_integrations_company
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_agentic_intelligence_v1"
down_revision = "0002_integrations_company"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["governance_runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_findings_run_id", "agent_findings", ["run_id"])
    op.create_index("ix_agent_findings_tenant_id", "agent_findings", ["tenant_id"])
    op.create_index("ix_agent_findings_agent_name", "agent_findings", ["agent_name"])
    op.create_index("ix_agent_findings_domain", "agent_findings", ["domain"])

    op.create_table(
        "correlated_incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("consensus_score", sa.Float(), nullable=False),
        sa.Column("conflict_detected", sa.Boolean(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("recommendation_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["governance_runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_correlated_incidents_run_id", "correlated_incidents", ["run_id"])
    op.create_index("ix_correlated_incidents_tenant_id", "correlated_incidents", ["tenant_id"])
    op.create_index("ix_correlated_incidents_status", "correlated_incidents", ["status"])
    op.create_index("ix_correlated_incidents_severity", "correlated_incidents", ["severity"])

    op.create_table(
        "executive_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("summary_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("xi_score", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["governance_runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executive_summaries_tenant_id", "executive_summaries", ["tenant_id"])
    op.create_index("ix_executive_summaries_run_id", "executive_summaries", ["run_id"])
    op.create_index("ix_executive_summaries_summary_type", "executive_summaries", ["summary_type"])


def downgrade() -> None:
    op.drop_index("ix_executive_summaries_summary_type", table_name="executive_summaries")
    op.drop_index("ix_executive_summaries_run_id", table_name="executive_summaries")
    op.drop_index("ix_executive_summaries_tenant_id", table_name="executive_summaries")
    op.drop_table("executive_summaries")

    op.drop_index("ix_correlated_incidents_severity", table_name="correlated_incidents")
    op.drop_index("ix_correlated_incidents_status", table_name="correlated_incidents")
    op.drop_index("ix_correlated_incidents_tenant_id", table_name="correlated_incidents")
    op.drop_index("ix_correlated_incidents_run_id", table_name="correlated_incidents")
    op.drop_table("correlated_incidents")

    op.drop_index("ix_agent_findings_domain", table_name="agent_findings")
    op.drop_index("ix_agent_findings_agent_name", table_name="agent_findings")
    op.drop_index("ix_agent_findings_tenant_id", table_name="agent_findings")
    op.drop_index("ix_agent_findings_run_id", table_name="agent_findings")
    op.drop_table("agent_findings")
