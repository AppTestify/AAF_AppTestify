"""Governance Copilot V1 run/case/decision/audit APIs."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Generic, Optional, TypeVar

T = TypeVar("T")

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from aaf.config import get_settings
from app.db import get_db
from app.deps import get_current_active_user, require_permission
from app.models.config import TenantSettings
from app.models.governance import AuditEvent, Decision, DecisionAction, EvidenceSnapshot, GovernanceCase, GovernanceRun, PortfolioProject
from app.services.action_automation import get_automation_config, queue_decision_actions, queue_run_actions
from app.models.metrics import LLMCallLog
from app.models.tenant import Tenant
from app.models.user import User
from guardrails.budget_cap import enforce_budget_cap
from guardrails.exceptions import GuardrailBlockedError
from guardrails.pm_prompt_guard import check_pm_prompt
from app.models.config import TenantSettings
from app.services.config_resolver import apply_pipeline_overrides, resolve_effective_settings, resolve_tenant_for_user
from app.services.run_jobs import enqueue_run
from app.services.share_link import mint_governance_share_token

router = APIRouter(prefix="/governance", tags=["governance-v1"])


class CreateRunBody(BaseModel):
    prompt: str = Field(min_length=1)
    prompt_id: Optional[str] = None
    portfolio_project_id: Optional[int] = None


class ShareLinkBody(BaseModel):
    expires_in_hours: int = Field(default=168, ge=1, le=8760)


class ShareLinkOut(BaseModel):
    url: str
    expires_at: datetime


class RunOut(BaseModel):
    id: int
    status: str
    prompt: str
    prompt_id: Optional[str] = None
    tenant_id: Optional[int] = None
    portfolio_project_id: Optional[int] = None
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
    portfolio_project_id: Optional[int] = None


class CaseOut(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    portfolio_project_id: Optional[int] = None
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
    portfolio_project_id: Optional[int] = None


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


class DecisionActionOut(BaseModel):
    id: int
    decision_id: int
    action_type: str
    state: str
    payload_json: dict[str, Any] = Field(default_factory=dict)
    result_json: Optional[dict[str, Any]] = None
    created_at: datetime
    finished_at: Optional[datetime] = None


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


class EvidenceOut(BaseModel):
    id: int
    run_id: int
    connector_name: str
    payload_json: dict
    created_at: datetime


class PaginatedOut(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


def _validate_portfolio_project_for_context(
    db: Session,
    current: User,
    tenant: Optional[Tenant],
    portfolio_project_id: Optional[int],
) -> Optional[int]:
    if portfolio_project_id is None:
        return None
    project = db.get(PortfolioProject, portfolio_project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio project not found")
    if not current.is_superadmin:
        if project.tenant_id != current.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this portfolio project")
        return portfolio_project_id
    if tenant is not None and project.tenant_id is not None and project.tenant_id != tenant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Portfolio project is not in the selected tenant context"
        )
    return portfolio_project_id


def _validate_portfolio_project_for_case_row(
    db: Session,
    current: User,
    case_row: GovernanceCase,
    portfolio_project_id: Optional[int],
) -> Optional[int]:
    if portfolio_project_id is None:
        return None
    project = db.get(PortfolioProject, portfolio_project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio project not found")
    if not current.is_superadmin:
        if project.tenant_id != current.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this portfolio project")
        return portfolio_project_id
    if case_row.tenant_id is not None and project.tenant_id is not None and project.tenant_id != case_row.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Portfolio project is not in the same tenant as this case"
        )
    return portfolio_project_id


def _case_out(row: GovernanceCase) -> CaseOut:
    return CaseOut(
        id=row.id,
        tenant_id=row.tenant_id,
        portfolio_project_id=row.portfolio_project_id,
        title=row.title,
        status=row.status,
        owner_user_id=row.owner_user_id,
        latest_run_id=row.latest_run_id,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _run_out(row: GovernanceRun) -> RunOut:
    return RunOut(
        id=row.id,
        status=row.status,
        prompt=row.prompt,
        prompt_id=row.prompt_id,
        tenant_id=row.tenant_id,
        portfolio_project_id=row.portfolio_project_id,
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
    settings = get_settings()
    effective = resolve_effective_settings(db, settings, tenant)
    ts_row = (
        db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
        if tenant
        else None
    )
    effective = apply_pipeline_overrides(effective, ts_row)
    if effective.guardrails_enabled and tenant:
        try:
            enforce_budget_cap(db, tenant.id, ts_row, effective)
        except GuardrailBlockedError as exc:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "budget_exceeded",
                    "guard": exc.result.guard_name,
                    "violations": [v.model_dump() for v in exc.result.violations],
                },
            ) from exc
    sanitized_prompt = body.prompt.strip()
    if effective.guardrails_enabled:
        guard = check_pm_prompt(body.prompt, effective)
        if guard.blocked:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "guardrail_blocked",
                    "guard": guard.guard_name,
                    "violations": [v.model_dump() for v in guard.violations],
                },
            )
        sanitized_prompt = guard.sanitized_prompt
    portfolio_project_id = _validate_portfolio_project_for_context(db, current, tenant, body.portfolio_project_id)
    run = GovernanceRun(
        tenant_id=tenant.id if tenant else None,
        requested_by_user_id=current.id,
        prompt=sanitized_prompt,
        prompt_id=body.prompt_id,
        portfolio_project_id=portfolio_project_id,
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


async def _run_sse_events(run_id: int, db_factory) -> AsyncIterator[str]:
    last_status = None
    for _ in range(120):
        db = db_factory()
        try:
            run = db.get(GovernanceRun, run_id)
            if run is None:
                yield f"event: error\ndata: {json.dumps({'detail': 'not_found'})}\n\n"
                return
            status_val = run.status
            if status_val != last_status:
                last_status = status_val
                yield f"event: status\ndata: {json.dumps({'status': status_val, 'run_id': run_id})}\n\n"
                if status_val == "running":
                    yield f"event: evidence_fetched\ndata: {json.dumps({'run_id': run_id})}\n\n"
                if status_val == "succeeded":
                    result = run.result_json or {}
                    yield f"event: agent_complete\ndata: {json.dumps({'agents': len(result.get('agent_opinions') or [])})}\n\n"
                    rar = result.get("rar") or {}
                    if rar.get("rar_triggered"):
                        yield f"event: rar_loop\ndata: {json.dumps(rar)}\n\n"
                    yield f"event: result_ready\ndata: {json.dumps({'run_id': run_id, 'consensus': (result.get('consensus') or {}).get('consensus_score')})}\n\n"
                    return
                if status_val == "failed":
                    yield f"event: error\ndata: {json.dumps({'error': run.error_message})}\n\n"
                    return
        finally:
            db.close()
        await asyncio.sleep(1)
    yield f"event: timeout\ndata: {json.dumps({'run_id': run_id})}\n\n"


@router.get("/runs/{run_id}/stream")
async def stream_run_v1(
    run_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    run = db.get(GovernanceRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not current.is_superadmin and current.tenant_id != run.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")

    from app.db import SessionLocal

    return StreamingResponse(
        _run_sse_events(run_id, SessionLocal),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/runs/{run_id}/llm-log")
def run_llm_log_v1(
    run_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    run = db.get(GovernanceRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not current.is_superadmin and current.tenant_id != run.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")
    rows = db.execute(select(LLMCallLog).where(LLMCallLog.run_id == run_id)).scalars().all()
    return {
        "run_id": run_id,
        "calls": [
            {
                "agent_id": r.agent_id,
                "provider_name": r.provider_name,
                "model_name": r.model_name,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "cost_usd": r.cost_usd,
                "latency_ms": r.latency_ms,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }


@router.delete("/tenant/data")
def delete_tenant_data_v1(
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    """GDPR-style tenant data purge (superadmin only). Retains audit_events."""
    if not current.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
    tenant = resolve_tenant_for_user(db, current, tenant_slug)
    if tenant is None:
        raise HTTPException(status_code=400, detail="tenant_required")
    run_ids = [
        r.id
        for r in db.execute(select(GovernanceRun).where(GovernanceRun.tenant_id == tenant.id)).scalars().all()
    ]
    if run_ids:
        db.execute(delete(EvidenceSnapshot).where(EvidenceSnapshot.run_id.in_(run_ids)))
        db.execute(delete(LLMCallLog).where(LLMCallLog.run_id.in_(run_ids)))
    db.execute(delete(GovernanceRun).where(GovernanceRun.tenant_id == tenant.id))
    db.execute(delete(GovernanceCase).where(GovernanceCase.tenant_id == tenant.id))
    db.commit()
    return {"status": "purged", "tenant_id": tenant.id, "runs_deleted": len(run_ids)}


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


@router.post("/runs/{run_id}/share-link", response_model=ShareLinkOut)
def create_run_share_link(
    run_id: int,
    body: ShareLinkBody,
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    settings = get_settings()
    run = db.get(GovernanceRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not current.is_superadmin and current.tenant_id != run.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")
    if run.tenant_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Run is not tenant-scoped")
    if run.status != "succeeded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Share links are only available for succeeded runs",
        )
    ttl = body.expires_in_hours * 3600
    from app.services.share_link import build_public_share_url

    token = mint_governance_share_token(run_id=run.id, tenant_id=run.tenant_id, ttl_seconds=ttl)
    url = build_public_share_url(token)
    exp = datetime.fromtimestamp(int(time.time()) + ttl, tz=timezone.utc)
    return ShareLinkOut(url=url, expires_at=exp)


@router.get("/runs", response_model=PaginatedOut[RunOut])
def list_runs_v1(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    prompt_contains: Optional[str] = Query(default=None),
    portfolio_project_id: Optional[int] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(GovernanceRun)
    if not current.is_superadmin:
        q = q.where(GovernanceRun.tenant_id == current.tenant_id)
    if status_filter:
        q = q.where(GovernanceRun.status == status_filter)
    if prompt_contains:
        q = q.where(GovernanceRun.prompt.ilike(f"%{prompt_contains.strip()}%"))
    if portfolio_project_id is not None:
        q = q.where(GovernanceRun.portfolio_project_id == portfolio_project_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = (
        db.execute(q.order_by(GovernanceRun.created_at.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return PaginatedOut(items=[_run_out(r) for r in rows], total=total, limit=limit, offset=offset)


@router.post("/cases", response_model=CaseOut, status_code=status.HTTP_201_CREATED)
def create_case(
    body: CaseCreateBody,
    tenant_slug: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    tenant = resolve_tenant_for_user(db, current, tenant_slug)
    effective_project_id: Optional[int] = body.portfolio_project_id
    if body.run_id is not None:
        run = db.get(GovernanceRun, body.run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        if not current.is_superadmin and current.tenant_id != run.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")
        if body.portfolio_project_id is None:
            effective_project_id = run.portfolio_project_id
        elif run.portfolio_project_id is not None and body.portfolio_project_id != run.portfolio_project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="portfolio_project_id does not match the linked run's portfolio project",
            )
    portfolio_project_id = _validate_portfolio_project_for_context(db, current, tenant, effective_project_id)
    case = GovernanceCase(
        tenant_id=tenant.id if tenant else None,
        title=body.title.strip(),
        status="new",
        owner_user_id=body.owner_user_id,
        latest_run_id=body.run_id,
        portfolio_project_id=portfolio_project_id,
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
    try:
        from app.services.notification_router import deliver_case_created

        deliver_case_created(case.id)
    except Exception:  # noqa: BLE001
        pass
    try:
        from app.services.search_index import index_governance_case

        index_governance_case(case)
    except Exception:  # noqa: BLE001
        pass
    return _case_out(case)


@router.get("/cases", response_model=PaginatedOut[CaseOut])
def list_cases(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    title_contains: Optional[str] = Query(default=None),
    portfolio_project_id: Optional[int] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(GovernanceCase)
    if not current.is_superadmin:
        q = q.where(GovernanceCase.tenant_id == current.tenant_id)
    if status_filter:
        q = q.where(GovernanceCase.status == status_filter)
    if title_contains:
        q = q.where(GovernanceCase.title.ilike(f"%{title_contains.strip()}%"))
    if portfolio_project_id is not None:
        q = q.where(GovernanceCase.portfolio_project_id == portfolio_project_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = (
        db.execute(q.order_by(GovernanceCase.updated_at.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return PaginatedOut(items=[_case_out(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/evidence", response_model=PaginatedOut[EvidenceOut])
def list_evidence(
    connector: Optional[str] = Query(default=None),
    run_id: Optional[int] = Query(default=None),
    portfolio_project_id: Optional[int] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(EvidenceSnapshot).join(GovernanceRun, GovernanceRun.id == EvidenceSnapshot.run_id)
    if not current.is_superadmin:
        q = q.where(GovernanceRun.tenant_id == current.tenant_id)
    if connector:
        q = q.where(EvidenceSnapshot.connector_name == connector)
    if run_id is not None:
        q = q.where(EvidenceSnapshot.run_id == run_id)
    if portfolio_project_id is not None:
        q = q.where(GovernanceRun.portfolio_project_id == portfolio_project_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = (
        db.execute(q.order_by(EvidenceSnapshot.created_at.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return PaginatedOut(
        items=[EvidenceOut(**r.__dict__) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/cases/{case_id}", response_model=CaseOut)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    row = db.get(GovernanceCase, case_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    if not current.is_superadmin and current.tenant_id != row.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this case")
    return _case_out(row)


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

    effective_project_for_run_check = (
        body.portfolio_project_id if body.portfolio_project_id is not None else row.portfolio_project_id
    )
    if body.latest_run_id is not None:
        linked_run = db.get(GovernanceRun, body.latest_run_id)
        if linked_run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
        if not current.is_superadmin and current.tenant_id != linked_run.tenant_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")
        if (
            effective_project_for_run_check is not None
            and linked_run.portfolio_project_id is not None
            and effective_project_for_run_check != linked_run.portfolio_project_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="latest_run_id does not match the case portfolio project",
            )
        row.latest_run_id = body.latest_run_id

    if body.portfolio_project_id is not None:
        _validate_portfolio_project_for_case_row(db, current, row, body.portfolio_project_id)
        run_id_check = row.latest_run_id
        if run_id_check is not None:
            linked_run = db.get(GovernanceRun, run_id_check)
            if (
                linked_run is not None
                and linked_run.portfolio_project_id is not None
                and linked_run.portfolio_project_id != body.portfolio_project_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="portfolio_project_id does not match the case latest run's portfolio project",
                )
        row.portfolio_project_id = body.portfolio_project_id
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
    try:
        from app.services.search_index import index_governance_case

        index_governance_case(row)
    except Exception:  # noqa: BLE001
        pass
    return _case_out(row)


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
    settings_row = (
        db.execute(select(TenantSettings).where(TenantSettings.tenant_id == case.tenant_id)).scalar_one_or_none()
        if case.tenant_id
        else None
    )
    config = get_automation_config(settings_row)
    if config.get("enabled"):
        tenant = db.get(Tenant, case.tenant_id) if case.tenant_id else None
        run = db.get(GovernanceRun, row.run_id) if row.run_id else None
        queue_decision_actions(
            db,
            decision=row,
            tenant=tenant,
            settings_row=settings_row,
            actor_user_id=current.id,
            run=run,
        )
    db.commit()
    db.refresh(row)
    return DecisionOut(**row.__dict__)


@router.post("/decisions/{decision_id}/execute-actions", response_model=list[DecisionActionOut])
def execute_decision_actions(
    decision_id: int,
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
    settings_row = (
        db.execute(select(TenantSettings).where(TenantSettings.tenant_id == case.tenant_id)).scalar_one_or_none()
        if case.tenant_id
        else None
    )
    tenant = db.get(Tenant, case.tenant_id) if case.tenant_id else None
    run = db.get(GovernanceRun, row.run_id) if row.run_id else None
    actions = queue_decision_actions(
        db,
        decision=row,
        tenant=tenant,
        settings_row=settings_row,
        actor_user_id=current.id,
        run=run,
    )
    db.commit()
    for action in actions:
        db.refresh(action)
    return [DecisionActionOut(**a.__dict__) for a in actions]


@router.get("/decisions/{decision_id}/actions", response_model=list[DecisionActionOut])
def list_decision_actions(
    decision_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    row = db.get(Decision, decision_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    case = db.get(GovernanceCase, row.case_id)
    if case and not current.is_superadmin and current.tenant_id != case.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this decision")
    actions = db.execute(select(DecisionAction).where(DecisionAction.decision_id == decision_id)).scalars().all()
    return [DecisionActionOut(**a.__dict__) for a in actions]


@router.post("/runs/{run_id}/execute-actions", response_model=list[DecisionActionOut])
def execute_run_actions(
    run_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("decisions.approve")),
):
    run = db.get(GovernanceRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not current.is_superadmin and current.tenant_id != run.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")
    settings_row = (
        db.execute(select(TenantSettings).where(TenantSettings.tenant_id == run.tenant_id)).scalar_one_or_none()
        if run.tenant_id
        else None
    )
    tenant = db.get(Tenant, run.tenant_id) if run.tenant_id else None
    actions = queue_run_actions(
        db,
        run=run,
        tenant=tenant,
        settings_row=settings_row,
        actor_user_id=current.id,
    )
    db.commit()
    for action in actions:
        db.refresh(action)
    return [DecisionActionOut(**a.__dict__) for a in actions]


@router.get("/audit-events", response_model=PaginatedOut[AuditOut])
def list_audit_events(
    area: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    q = select(AuditEvent)
    if area:
        q = q.where(AuditEvent.area == area)
    if severity:
        q = q.where(AuditEvent.severity == severity)
    if not current.is_superadmin:
        q = q.where(AuditEvent.tenant_id == current.tenant_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = (
        db.execute(q.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    return PaginatedOut(
        items=[AuditOut(**r.__dict__) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/audit-events/{event_id}/acknowledge", response_model=AuditOut)
def acknowledge_audit_event(
    event_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    row = db.get(AuditEvent, event_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")
    if not current.is_superadmin and current.tenant_id != row.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this audit event")
    ack = AuditEvent(
        tenant_id=row.tenant_id,
        actor_user_id=current.id,
        area="alerts",
        action="acknowledged",
        entity_type="audit_event",
        entity_id=row.id,
        severity="info",
        summary=f"Alert {row.id} acknowledged",
    )
    db.add(ack)
    db.commit()
    db.refresh(ack)
    return AuditOut(**ack.__dict__)
