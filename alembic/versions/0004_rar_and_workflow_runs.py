"""add rar iterations and workflow runs

Revision ID: 0004_rar_and_workflow_runs
Revises: 0003_agentic_intelligence_v1
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004_rar_and_workflow_runs"
down_revision = "0003_agentic_intelligence_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rar_iterations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("incident_id", sa.Integer(), nullable=False),
        sa.Column("iteration_index", sa.Integer(), nullable=False),
        sa.Column("trigger_reason", sa.String(length=128), nullable=False),
        sa.Column("confidence_before", sa.Float(), nullable=False),
        sa.Column("confidence_after", sa.Float(), nullable=False),
        sa.Column("evidence_enrichment_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["correlated_incidents.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rar_iterations_tenant_id", "rar_iterations", ["tenant_id"])
    op.create_index("ix_rar_iterations_incident_id", "rar_iterations", ["incident_id"])

    op.create_table(
        "governance_workflow_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("incident_id", sa.Integer(), nullable=True),
        sa.Column("workflow_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("decision", sa.String(length=64), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["incident_id"], ["correlated_incidents.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_governance_workflow_runs_tenant_id", "governance_workflow_runs", ["tenant_id"])
    op.create_index("ix_governance_workflow_runs_incident_id", "governance_workflow_runs", ["incident_id"])
    op.create_index("ix_governance_workflow_runs_workflow_type", "governance_workflow_runs", ["workflow_type"])
    op.create_index("ix_governance_workflow_runs_status", "governance_workflow_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_governance_workflow_runs_status", table_name="governance_workflow_runs")
    op.drop_index("ix_governance_workflow_runs_workflow_type", table_name="governance_workflow_runs")
    op.drop_index("ix_governance_workflow_runs_incident_id", table_name="governance_workflow_runs")
    op.drop_index("ix_governance_workflow_runs_tenant_id", table_name="governance_workflow_runs")
    op.drop_table("governance_workflow_runs")

    op.drop_index("ix_rar_iterations_incident_id", table_name="rar_iterations")
    op.drop_index("ix_rar_iterations_tenant_id", table_name="rar_iterations")
    op.drop_table("rar_iterations")
