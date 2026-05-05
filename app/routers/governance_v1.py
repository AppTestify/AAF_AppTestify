"""Governance Copilot V1 run/case/decision/audit APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, require_permission
from app.models.governance import AuditEvent, Decision, GovernanceCase, GovernanceRun
from app.models.user import User
from app.services.config_resolver import resolve_tenant_for_user
from app.services.run_jobs import enqueue_run

router = APIRouter(prefix="/governance", tags=["governance-v1"])


class CreateRunBody(BaseModel):
    prompt: str = Field(min_length=1)
    prompt_id: Optional[str] = None


class RunOut(BaseModel):
    id: int
    status: str
    prompt: str
    prompt_id: Optional[str] = None
    tenant_id: Optional[int] = None
    retry_count: int
    error_message: Optional[str] = None
    runtime_config_json: dict
    result_json: Optional[dict] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class CaseCreateBody(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    run_id: Optional[int] = None
    owner_user_id: Optional[int] = None


class CaseOut(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    title: str
    status: str
    owner_user_id: Optional[int] = None
    latest_run_id: Optional[int] = None
    created_by_user_id: int
    created_at: datetime
    updated_at: datetime


class CasePatchBody(BaseModel):
    status: Optional[str] = None
    owner_user_id: Optional[int] = None
    latest_run_id: Optional[int] = None


class DecisionCreateBody(BaseModel):
    run_id: Optional[int] = None
    recommended_action: Optional[str] = None
    rationale: Optional[str] = None


class DecisionApproveBody(BaseModel):
    final_action: str = Field(min_length=1)
    rationale: Optional[str] = None


class DecisionOut(BaseModel):
    id: int
    case_id: int
    run_id: Optional[int] = None
    status: str
    recommended_action: Optional[str] = None
    final_action: Optional[str] = None
    rationale: Optional[str] = None
    approved_by_user_id: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_by_user_id: int
    created_at: datetime


class AuditOut(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    actor_user_id: int
    area: str
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    severity: str
    summary: str
    created_at: datetime


def _run_out(row: GovernanceRun) -> RunOut:
    return RunOut(
        id=row.id,
        status=row.status,
        prompt=row.prompt,
        prompt_id=row.prompt_id,
        tenant_id=row.tenant_id,
        retry_count=row.retry_count,
        error_message=row.error_message,
        runtime_config_json=row.runtime_config_json,
        result_json=row.result_json,
        created_at=row.created_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
    )


@router.post("/runs", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
def create_run_v1(
    body: CreateRunBody,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("runs.create")),
):
    tenant = resolve_tenant_for_user(db, current, tenant_slug)
    run = GovernanceRun(
        tenant_id=tenant.id if tenant else None,
        requested_by_user_id=current.id,
        prompt=body.prompt.strip(),
        prompt_id=body.prompt_id,
        status="queued",
        runtime_config_json={"tenant_slug": tenant.slug if tenant else None},
    )
    db.add(run)
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=run.tenant_id,
            actor_user_id=current.id,
            area="governance_run",
            action="queued",
            entity_type="governance_run",
            entity_id=run.id,
            summary=f"Run {run.id} queued",
        )
    )
    db.commit()
    enqueue_run(run.id)
    db.refresh(run)
    return _run_out(run)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run_v1(
    run_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    run = db.get(GovernanceRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not current.is_superadmin and current.tenant_id != run.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")
    return _run_out(run)


@router.get("/runs", response_model=list[RunOut])
def list_runs_v1(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(GovernanceRun).order_by(GovernanceRun.created_at.desc()).limit(limit)
    if not current.is_superadmin:
        q = q.where(GovernanceRun.tenant_id == current.tenant_id)
    if status_filter:
        q = q.where(GovernanceRun.status == status_filter)
    rows = db.execute(q).scalars().all()
    return [_run_out(r) for r in rows]


@router.post("/cases", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    body: CaseCreateBody,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    tenant = resolve_tenant_for_user(db, current, tenant_slug)
    case = GovernanceCase(
        tenant_id=tenant.id if tenant else None,
        title=body.title.strip(),
        status="new",
        owner_user_id=body.owner_user_id,
        latest_run_id=body.run_id,
        created_by_user_id=current.id,
    )
    db.add(case)
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=case.tenant_id,
            actor_user_id=current.id,
            area="governance_case",
            action="created",
            entity_type="governance_case",
            entity_id=case.id,
            summary=f"Case {case.id} created",
        )
    )
    db.commit()
    db.refresh(case)
    return CaseOut(**case.__dict__)


@router.get("/cases", response_model=list[CaseOut])
def list_cases(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(GovernanceCase).order_by(GovernanceCase.updated_at.desc()).limit(limit)
    if not current.is_superadmin:
        q = q.where(GovernanceCase.tenant_id == current.tenant_id)
    rows = db.execute(q).scalars().all()
    return [CaseOut(**r.__dict__) for r in rows]


@router.patch("/cases/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    body: CasePatchBody,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    row = db.get(GovernanceCase, case_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not current.is_superadmin and current.tenant_id != row.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this case")
    if body.status is not None:
        row.status = body.status
    if body.owner_user_id is not None:
        row.owner_user_id = body.owner_user_id
    if body.latest_run_id is not None:
        row.latest_run_id = body.latest_run_id
    row.updated_at = datetime.now(timezone.utc)
    db.add(
        AuditEvent(
            tenant_id=row.tenant_id,
            actor_user_id=current.id,
            area="governance_case",
            action="updated",
            entity_type="governance_case",
            entity_id=row.id,
            summary=f"Case {row.id} updated",
        )
    )
    db.commit()
    db.refresh(row)
    return CaseOut(**row.__dict__)


@router.post("/cases/{case_id}/decisions", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
def create_decision(
    case_id: int,
    body: DecisionCreateBody,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    case = db.get(GovernanceCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not current.is_superadmin and current.tenant_id != case.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this case")
    row = Decision(
        case_id=case_id,
        run_id=body.run_id,
        status="proposed",
        recommended_action=body.recommended_action,
        rationale=body.rationale,
        created_by_user_id=current.id,
    )
    db.add(row)
    db.flush()
    db.add(
        AuditEvent(
            tenant_id=case.tenant_id,
            actor_user_id=current.id,
            area="decision",
            action="created",
            entity_type="decision",
            entity_id=row.id,
            summary=f"Decision {row.id} created for case {case.id}",
        )
    )
    db.commit()
    db.refresh(row)
    return DecisionOut(**row.__dict__)


@router.post("/decisions/{decision_id}/approve", response_model=DecisionOut)
def approve_decision(
    decision_id: int,
    body: DecisionApproveBody,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("decisions.approve")),
):
    row = db.get(Decision, decision_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    case = db.get(GovernanceCase, row.case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not current.is_superadmin and current.tenant_id != case.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this decision")
    row.status = "approved"
    row.final_action = body.final_action
    row.rationale = body.rationale or row.rationale
    row.approved_by_user_id = current.id
    row.approved_at = datetime.now(timezone.utc)
    db.add(
        AuditEvent(
            tenant_id=case.tenant_id,
            actor_user_id=current.id,
            area="decision",
            action="approved",
            entity_type="decision",
            entity_id=row.id,
            summary=f"Decision {row.id} approved",
        )
    )
    db.commit()
    db.refresh(row)
    return DecisionOut(**row.__dict__)


@router.get("/audit-events", response_model=list[AuditOut])
def list_audit_events(
    area: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    q = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if area:
        q = q.where(AuditEvent.area == area)
    if not current.is_superadmin:
        q = q.where(AuditEvent.tenant_id == current.tenant_id)
    rows = db.execute(q).scalars().all()
    return [AuditOut(**r.__dict__) for r in rows]
