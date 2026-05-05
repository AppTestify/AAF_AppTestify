"""User account for auth (multi-tenant)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    """Platform super-admin: full tenant and user management; not scoped to a tenant."""
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """Tenant administrator (manage users/settings within one tenant)."""
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tenant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tenants.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", lazy="joined")
