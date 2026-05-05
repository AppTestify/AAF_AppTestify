"""Tenant governance policy thresholds."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class GovernancePolicy(Base):
    __tablename__ = "governance_policies"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_policy_tenant_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    consensus_min: Mapped[float] = mapped_column(Float, default=0.55, nullable=False)
    xi_min: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    require_rar_clear: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
