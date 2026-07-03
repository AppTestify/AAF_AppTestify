"""Roadmap metrics: deployment_events, llm_call_logs, services."""

from alembic import op
import sqlalchemy as sa

revision = "0010_roadmap_metrics"
down_revision = "90fc4c5ab223"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deployment_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("service_name", sa.String(128), nullable=False),
        sa.Column("environment", sa.String(32), nullable=False, server_default="production"),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lead_time_hours", sa.Float(), nullable=True),
        sa.Column("succeeded", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("rollback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deployment_events_tenant_id", "deployment_events", ["tenant_id"])
    op.create_index("ix_deployment_events_deployed_at", "deployment_events", ["deployed_at"])

    op.create_table(
        "llm_call_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("agent_id", sa.String(64), nullable=False),
        sa.Column("provider_name", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["governance_runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_call_logs_run_id", "llm_call_logs", ["run_id"])

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_project_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("tier", sa.String(16), nullable=False, server_default="tier2"),
        sa.Column("repo_url", sa.String(512), nullable=True),
        sa.Column("slo_json", sa.JSON(), nullable=False),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["portfolio_project_id"], ["portfolio_projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_services_tenant_id", "services", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("services")
    op.drop_table("llm_call_logs")
    op.drop_table("deployment_events")
