"""Project portfolio and release governance APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, require_permission
from app.models.governance import (
    AuditEvent,
    Decision,
    EvidenceSnapshot,
    GovernanceCase,
    GovernanceRun,
    PortfolioProject,
    ProjectRelease,
)
from app.models.user import User

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


class ProjectIn(BaseModel):
    key: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    owner: Optional[str] = None
    status: str = "active"


class ProjectOut(ProjectIn):
    model_config = {"from_attributes": True}
    id: int
    tenant_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class ReleaseIn(BaseModel):
    project_id: int
    version: str = Field(min_length=1, max_length=64)
    target_date: Optional[datetime] = None
    status: str = "planned"
    release_decision: Optional[str] = None
    decision_confidence: Optional[float] = None
    consensus_score: Optional[float] = None
    risk_level: Optional[str] = None
    run_id: Optional[int] = None


class ReleaseOut(ReleaseIn):
    model_config = {"from_attributes": True}
    id: int
    tenant_id: Optional[int] = None
    metadata_json: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class ExecutivePortfolioReport(BaseModel):
    projects_total: int
    active_projects: int
    releases_total: int
    releases_planned: int
    releases_approved: int
    releases_blocked: int
    avg_confidence: float
    avg_consensus: float
    high_risk_open: int
    project_breakdown: list[dict]


class PortfolioOperationsContextOut(BaseModel):
    """Tenant-scoped operational metrics that complement portfolio releases (same scope as Dashboard)."""

    runs_total: int
    runs_24h: int
    runs_success_24h: int
    cases_open: int
    cases_total: int
    alerts_24h: int
    evidence_snapshots_total: int
    decisions_total: int
    decisions_approved: int
    portfolio_releases_total: int
    portfolio_releases_linked_to_run: int


def _tenant_scope(q, col, current: User):
    if current.is_superadmin:
        return q
    return q.where(col == current.tenant_id)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(PortfolioProject).order_by(PortfolioProject.updated_at.desc())
    q = _tenant_scope(q, PortfolioProject.tenant_id, current)
    if status_filter:
        q = q.where(PortfolioProject.status == status_filter)
    rows = db.execute(q).scalars().all()
    return [ProjectOut.model_validate(r) for r in rows]


@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    row = PortfolioProject(
        tenant_id=None if current.is_superadmin else current.tenant_id,
        key=body.key.strip().upper(),
        name=body.name.strip(),
        owner=body.owner,
        status=body.status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ProjectOut.model_validate(row)


@router.get("/releases", response_model=list[ReleaseOut])
def list_releases(
    project_id: Optional[int] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(ProjectRelease).order_by(ProjectRelease.updated_at.desc())
    q = _tenant_scope(q, ProjectRelease.tenant_id, current)
    if project_id is not None:
        q = q.where(ProjectRelease.project_id == project_id)
    if status_filter:
        q = q.where(ProjectRelease.status == status_filter)
    rows = db.execute(q).scalars().all()
    return [ReleaseOut.model_validate(r) for r in rows]


@router.post("/releases", response_model=ReleaseOut, status_code=status.HTTP_201_CREATED)
def create_release(
    body: ReleaseIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    project = db.get(PortfolioProject, body.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current.is_superadmin and project.tenant_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="Not allowed for this project")
    row = ProjectRelease(
        tenant_id=project.tenant_id,
        project_id=body.project_id,
        version=body.version,
        target_date=body.target_date,
        status=body.status,
        release_decision=body.release_decision,
        decision_confidence=body.decision_confidence,
        consensus_score=body.consensus_score,
        risk_level=body.risk_level,
        run_id=body.run_id,
        metadata_json={},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ReleaseOut.model_validate(row)


def build_executive_portfolio_report(db: Session, current: User) -> ExecutivePortfolioReport:
    """Shared executive portfolio payload for JSON and export endpoints."""
    projects_q = select(func.count(PortfolioProject.id), func.sum(case((PortfolioProject.status == "active", 1), else_=0)))
    releases_q = select(
        func.count(ProjectRelease.id),
        func.sum(case((ProjectRelease.status == "planned", 1), else_=0)),
        func.sum(case((ProjectRelease.release_decision == "go", 1), else_=0)),
        func.sum(case((ProjectRelease.release_decision == "hold", 1), else_=0)),
        func.avg(ProjectRelease.decision_confidence),
        func.avg(ProjectRelease.consensus_score),
        func.sum(case((ProjectRelease.risk_level == "critical", 1), else_=0)),
    )
    if not current.is_superadmin:
        projects_q = projects_q.where(PortfolioProject.tenant_id == current.tenant_id)
        releases_q = releases_q.where(ProjectRelease.tenant_id == current.tenant_id)
    projects_total, active_projects = db.execute(projects_q).one()
    (
        releases_total,
        releases_planned,
        releases_approved,
        releases_blocked,
        avg_confidence,
        avg_consensus,
        high_risk_open,
    ) = db.execute(releases_q).one()

    breakdown_q = (
        select(
            PortfolioProject.id,
            PortfolioProject.key,
            PortfolioProject.name,
            func.count(ProjectRelease.id),
            func.sum(case((ProjectRelease.release_decision == "go", 1), else_=0)),
            func.sum(case((ProjectRelease.release_decision == "hold", 1), else_=0)),
            func.avg(ProjectRelease.decision_confidence),
        )
        .join(ProjectRelease, ProjectRelease.project_id == PortfolioProject.id, isouter=True)
        .group_by(PortfolioProject.id)
        .order_by(PortfolioProject.updated_at.desc())
    )
    if not current.is_superadmin:
        breakdown_q = breakdown_q.where(PortfolioProject.tenant_id == current.tenant_id)
    breakdown_rows = db.execute(breakdown_q).all()
    return ExecutivePortfolioReport(
        projects_total=int(projects_total or 0),
        active_projects=int(active_projects or 0),
        releases_total=int(releases_total or 0),
        releases_planned=int(releases_planned or 0),
        releases_approved=int(releases_approved or 0),
        releases_blocked=int(releases_blocked or 0),
        avg_confidence=float(avg_confidence or 0.0),
        avg_consensus=float(avg_consensus or 0.0),
        high_risk_open=int(high_risk_open or 0),
        project_breakdown=[
            {
                "project_id": int(r[0]),
                "project_key": r[1],
                "project_name": r[2],
                "releases_total": int(r[3] or 0),
                "go_count": int(r[4] or 0),
                "hold_count": int(r[5] or 0),
                "avg_confidence": float(r[6] or 0.0),
            }
            for r in breakdown_rows
        ],
    )


@router.get("/reports/executive", response_model=ExecutivePortfolioReport)
def executive_portfolio_report(
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    return build_executive_portfolio_report(db, current)


def _governance_run_scope(current: User):
    if current.is_superadmin:
        return None
    return GovernanceRun.tenant_id == current.tenant_id


def _governance_case_scope(current: User):
    if current.is_superadmin:
        return None
    return GovernanceCase.tenant_id == current.tenant_id


def _audit_scope(current: User):
    if current.is_superadmin:
        return None
    return AuditEvent.tenant_id == current.tenant_id


@router.get("/reports/operations-context", response_model=PortfolioOperationsContextOut)
def portfolio_operations_context(
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    """Operational counts used on Dashboard / Runs / Cases / Alerts — scoped like telemetry summary."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    run_sc = _governance_run_scope(current)
    case_sc = _governance_case_scope(current)
    audit_sc = _audit_scope(current)

    runs_total_q = select(func.count(GovernanceRun.id))
    runs_24h_q = select(func.count(GovernanceRun.id)).where(GovernanceRun.created_at >= since)
    runs_ok_q = select(func.count(GovernanceRun.id)).where(
        GovernanceRun.created_at >= since, GovernanceRun.status == "succeeded"
    )
    if run_sc is not None:
        runs_total_q = runs_total_q.where(run_sc)
        runs_24h_q = runs_24h_q.where(run_sc)
        runs_ok_q = runs_ok_q.where(run_sc)

    cases_total_q = select(func.count(GovernanceCase.id))
    cases_open_q = select(func.count(GovernanceCase.id)).where(GovernanceCase.status.in_(["new", "in_review"]))
    if case_sc is not None:
        cases_total_q = cases_total_q.where(case_sc)
        cases_open_q = cases_open_q.where(case_sc)

    alerts_q = select(func.count(AuditEvent.id)).where(AuditEvent.created_at >= since)
    if audit_sc is not None:
        alerts_q = alerts_q.where(audit_sc)

    evidence_q = select(func.count(EvidenceSnapshot.id)).join(GovernanceRun, GovernanceRun.id == EvidenceSnapshot.run_id)
    if run_sc is not None:
        evidence_q = evidence_q.where(run_sc)

    decisions_q = select(func.count(Decision.id)).join(GovernanceCase, GovernanceCase.id == Decision.case_id)
    decisions_ok_q = (
        select(func.count(Decision.id))
        .join(GovernanceCase, GovernanceCase.id == Decision.case_id)
        .where(Decision.status == "approved")
    )
    if case_sc is not None:
        decisions_q = decisions_q.where(case_sc)
        decisions_ok_q = decisions_ok_q.where(case_sc)

    pr_total_q = select(func.count(ProjectRelease.id))
    pr_linked_q = select(func.count(ProjectRelease.id)).where(ProjectRelease.run_id.isnot(None))
    if not current.is_superadmin:
        pr_total_q = pr_total_q.where(ProjectRelease.tenant_id == current.tenant_id)
        pr_linked_q = pr_linked_q.where(ProjectRelease.tenant_id == current.tenant_id)

    return PortfolioOperationsContextOut(
        runs_total=int(db.scalar(runs_total_q) or 0),
        runs_24h=int(db.scalar(runs_24h_q) or 0),
        runs_success_24h=int(db.scalar(runs_ok_q) or 0),
        cases_open=int(db.scalar(cases_open_q) or 0),
        cases_total=int(db.scalar(cases_total_q) or 0),
        alerts_24h=int(db.scalar(alerts_q) or 0),
        evidence_snapshots_total=int(db.scalar(evidence_q) or 0),
        decisions_total=int(db.scalar(decisions_q) or 0),
        decisions_approved=int(db.scalar(decisions_ok_q) or 0),
        portfolio_releases_total=int(db.scalar(pr_total_q) or 0),
        portfolio_releases_linked_to_run=int(db.scalar(pr_linked_q) or 0),
    )
