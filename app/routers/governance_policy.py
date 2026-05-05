"""Tenant governance policy APIs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, require_permission
from app.models.governance import AuditEvent
from app.models.policy import GovernancePolicy
from app.models.user import User
from app.services.config_resolver import resolve_tenant_for_user

router = APIRouter(prefix="/governance/policies", tags=["governance-policy"])


class PolicyOut(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    name: str
    consensus_min: float
    xi_min: float
    require_rar_clear: bool


class PolicyPatch(BaseModel):
    consensus_min: float = Field(ge=0, le=1)
    xi_min: float = Field(ge=0, le=1)
    require_rar_clear: bool


@router.get("", response_model=list[PolicyOut])
def list_policies(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    tenant = resolve_tenant_for_user(db, current, tenant_slug)
    if tenant is None:
        return []
    rows = db.execute(select(GovernancePolicy).where(GovernancePolicy.tenant_id == tenant.id)).scalars().all()
    return [PolicyOut(**r.__dict__) for r in rows]


@router.put("/{policy_name}", response_model=PolicyOut)
def upsert_policy(
    policy_name: str,
    body: PolicyPatch,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("settings.manage")),
):
    tenant = resolve_tenant_for_user(db, current, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tenant context required")
    row = db.execute(
        select(GovernancePolicy).where(GovernancePolicy.tenant_id == tenant.id, GovernancePolicy.name == policy_name)
    ).scalar_one_or_none()
    if row is None:
        row = GovernancePolicy(tenant_id=tenant.id, name=policy_name)
        db.add(row)
    row.consensus_min = body.consensus_min
    row.xi_min = body.xi_min
    row.require_rar_clear = body.require_rar_clear
    db.add(
        AuditEvent(
            tenant_id=tenant.id,
            actor_user_id=current.id,
            area="governance_policy",
            action="upsert",
            entity_type="governance_policy",
            entity_id=row.id if row.id else None,
            summary=f"Policy {policy_name} updated",
            after_json={
                "consensus_min": row.consensus_min,
                "xi_min": row.xi_min,
                "require_rar_clear": row.require_rar_clear,
            },
        )
    )
    db.commit()
    db.refresh(row)
    return PolicyOut(**row.__dict__)
