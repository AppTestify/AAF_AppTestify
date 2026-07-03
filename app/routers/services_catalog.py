"""Service catalog API."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, require_permission
from app.models.metrics import Service
from app.models.user import User
from app.services.config_resolver import resolve_tenant_for_user

router = APIRouter(prefix="/services", tags=["services"])


class ServiceIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    owner: Optional[str] = None
    tier: str = "tier2"
    repo_url: Optional[str] = None
    slo_json: dict[str, Any] = Field(default_factory=dict)
    dependencies_json: list[str] = Field(default_factory=list)
    portfolio_project_id: Optional[int] = None


class ServiceOut(BaseModel):
    id: int
    tenant_id: int
    name: str
    owner: Optional[str] = None
    tier: str
    repo_url: Optional[str] = None
    slo_json: dict[str, Any]
    dependencies_json: list[str]
    portfolio_project_id: Optional[int] = None


@router.get("", response_model=list[ServiceOut])
def list_services(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    tenant = resolve_tenant_for_user(db, user, tenant_slug)
    if tenant is None:
        return []
    rows = db.execute(select(Service).where(Service.tenant_id == tenant.id)).scalars().all()
    return [
        ServiceOut(
            id=r.id,
            tenant_id=r.tenant_id,
            name=r.name,
            owner=r.owner,
            tier=r.tier,
            repo_url=r.repo_url,
            slo_json=r.slo_json or {},
            dependencies_json=r.dependencies_json or [],
            portfolio_project_id=r.portfolio_project_id,
        )
        for r in rows
    ]


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    body: ServiceIn,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings.manage")),
):
    tenant = resolve_tenant_for_user(db, user, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=400, detail="tenant_required")
    row = Service(
        tenant_id=tenant.id,
        name=body.name,
        owner=body.owner,
        tier=body.tier,
        repo_url=body.repo_url,
        slo_json=body.slo_json,
        dependencies_json=body.dependencies_json,
        portfolio_project_id=body.portfolio_project_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ServiceOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        owner=row.owner,
        tier=row.tier,
        repo_url=row.repo_url,
        slo_json=row.slo_json or {},
        dependencies_json=row.dependencies_json or [],
        portfolio_project_id=row.portfolio_project_id,
    )


@router.get("/{service_id}", response_model=ServiceOut)
def get_service(
    service_id: int,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    tenant = resolve_tenant_for_user(db, user, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    row = db.get(Service, service_id)
    if row is None or row.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return ServiceOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        owner=row.owner,
        tier=row.tier,
        repo_url=row.repo_url,
        slo_json=row.slo_json or {},
        dependencies_json=row.dependencies_json or [],
        portfolio_project_id=row.portfolio_project_id,
    )


@router.put("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int,
    body: ServiceIn,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings.manage")),
):
    tenant = resolve_tenant_for_user(db, user, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    row = db.get(Service, service_id)
    if row is None or row.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    row.name = body.name
    row.owner = body.owner
    row.tier = body.tier
    row.repo_url = body.repo_url
    row.slo_json = body.slo_json
    row.dependencies_json = body.dependencies_json
    row.portfolio_project_id = body.portfolio_project_id
    db.commit()
    db.refresh(row)
    return ServiceOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        owner=row.owner,
        tier=row.tier,
        repo_url=row.repo_url,
        slo_json=row.slo_json or {},
        dependencies_json=row.dependencies_json or [],
        portfolio_project_id=row.portfolio_project_id,
    )


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("settings.manage")),
):
    tenant = resolve_tenant_for_user(db, user, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    row = db.get(Service, service_id)
    if row is None or row.tenant_id != tenant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    db.delete(row)
    db.commit()
