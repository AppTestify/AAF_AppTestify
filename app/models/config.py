"""Tenant-scoped runtime configuration models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    default_ai_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ui_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantConnectorConfig(Base):
    __tablename__ = "tenant_connector_configs"
    __table_args__ = (UniqueConstraint("tenant_id", "connector_name", name="uq_tenant_connector_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    connector_name: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_validation_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    last_validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TenantAIProviderConfig(Base):
    __tablename__ = "tenant_ai_provider_configs"
    __table_args__ = (UniqueConstraint("tenant_id", "provider_name", name="uq_tenant_provider_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(nullable=True)
    max_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)
    endpoint_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    api_key_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    timeout_seconds: Mapped[Optional[int]] = mapped_column(nullable=True)
    retry_count: Mapped[Optional[int]] = mapped_column(nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_validation_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    last_validation_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConfigAuditLog(Base):
    __tablename__ = "config_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    area: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    before_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    after_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
