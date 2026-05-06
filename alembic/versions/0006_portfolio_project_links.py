"""link governance runs and cases to portfolio projects

Revision ID: 0006_portfolio_project_links
Revises: 0005_access_leads
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_portfolio_project_links"
down_revision = "0005_access_leads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    names = set(insp.get_table_names())

    if "portfolio_projects" not in names:
        op.create_table(
            "portfolio_projects",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("key", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("owner", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_portfolio_projects_tenant_id", "portfolio_projects", ["tenant_id"], unique=False)
        op.create_index("ix_portfolio_projects_key", "portfolio_projects", ["key"], unique=False)
        op.create_index("ix_portfolio_projects_status", "portfolio_projects", ["status"], unique=False)

    if "project_releases" not in names:
        op.create_table(
            "project_releases",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("tenant_id", sa.Integer(), nullable=True),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("version", sa.String(length=64), nullable=False),
            sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="planned"),
            sa.Column("release_decision", sa.String(length=64), nullable=True),
            sa.Column("decision_confidence", sa.Float(), nullable=True),
            sa.Column("consensus_score", sa.Float(), nullable=True),
            sa.Column("risk_level", sa.String(length=32), nullable=True),
            sa.Column("run_id", sa.Integer(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["portfolio_projects.id"]),
            sa.ForeignKeyConstraint(["run_id"], ["governance_runs.id"]),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_project_releases_tenant_id", "project_releases", ["tenant_id"], unique=False)
        op.create_index("ix_project_releases_project_id", "project_releases", ["project_id"], unique=False)
        op.create_index("ix_project_releases_version", "project_releases", ["version"], unique=False)
        op.create_index("ix_project_releases_status", "project_releases", ["status"], unique=False)
        op.create_index("ix_project_releases_run_id", "project_releases", ["run_id"], unique=False)

    op.add_column(
        "governance_runs",
        sa.Column("portfolio_project_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_governance_runs_portfolio_project_id",
        "governance_runs",
        "portfolio_projects",
        ["portfolio_project_id"],
        ["id"],
    )
    op.create_index("ix_governance_runs_portfolio_project_id", "governance_runs", ["portfolio_project_id"], unique=False)

    op.add_column(
        "governance_cases",
        sa.Column("portfolio_project_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_governance_cases_portfolio_project_id",
        "governance_cases",
        "portfolio_projects",
        ["portfolio_project_id"],
        ["id"],
    )
    op.create_index(
        "ix_governance_cases_portfolio_project_id", "governance_cases", ["portfolio_project_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_governance_cases_portfolio_project_id", table_name="governance_cases")
    op.drop_constraint("fk_governance_cases_portfolio_project_id", "governance_cases", type_="foreignkey")
    op.drop_column("governance_cases", "portfolio_project_id")

    op.drop_index("ix_governance_runs_portfolio_project_id", table_name="governance_runs")
    op.drop_constraint("fk_governance_runs_portfolio_project_id", "governance_runs", type_="foreignkey")
    op.drop_column("governance_runs", "portfolio_project_id")
