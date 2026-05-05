"""Superadmin-only tenant management."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_superadmin
from app.models.tenant import Tenant
from app.models.user import User

router = APIRouter(prefix="/admin/tenants", tags=["admin-tenants"])

_SLUG = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=64)

    @field_validator("slug")
    @classmethod
    def slug_ok(cls, v: str) -> str:
        s = v.strip().lower()
        if not _SLUG.match(s):
            raise ValueError(
                "slug must start with a letter and contain only lowercase letters, digits, and hyphens"
            )
        return s


class TenantOut(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool
    user_count: int = 0

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[TenantOut])
def list_tenants(
    db: Session = Depends(get_db),
    _super: User = Depends(require_superadmin),
):
    tenants = db.scalars(select(Tenant).order_by(Tenant.slug)).all()
    out: list[TenantOut] = []
    for tenant in tenants:
        uc = db.scalar(select(func.count(User.id)).where(User.tenant_id == tenant.id))
        out.append(
            TenantOut(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                is_active=tenant.is_active,
                user_count=int(uc or 0),
            )
        )
    return out


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(
    body: TenantCreate,
    db: Session = Depends(get_db),
    _super: User = Depends(require_superadmin),
):
    slug = body.slug
    dup = db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")
    tenant = Tenant(name=body.name.strip(), slug=slug, is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return TenantOut(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        is_active=tenant.is_active,
        user_count=0,
    )
