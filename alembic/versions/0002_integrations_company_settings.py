"""add integration secret and rag settings columns

Revision ID: 0002_integrations_company
Revises: 0001_governance_v1
Create Date: 2026-05-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_integrations_company"
down_revision = "0001_governance_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenant_settings", sa.Column("llm_keys_encrypted_json", sa.Text(), nullable=True))
    op.add_column("tenant_settings", sa.Column("rag_config_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    op.add_column("tenant_connector_configs", sa.Column("encrypted_credentials_json", sa.Text(), nullable=True))
    op.add_column(
        "tenant_connector_configs",
        sa.Column("telemetry_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column("tenant_connector_configs", sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("tenant_ai_provider_configs", sa.Column("api_key_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant_ai_provider_configs", "api_key_encrypted")
    op.drop_column("tenant_connector_configs", "last_sync_at")
    op.drop_column("tenant_connector_configs", "telemetry_json")
    op.drop_column("tenant_connector_configs", "encrypted_credentials_json")
    op.drop_column("tenant_settings", "rag_config_json")
    op.drop_column("tenant_settings", "llm_keys_encrypted_json")
