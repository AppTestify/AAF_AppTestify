"""Governance intelligence APIs (incidents, consensus, executive summaries)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user
from app.models.governance import CorrelatedIncident, ExecutiveSummary, GovernanceRun, GovernanceWorkflowRun, RARIteration
from app.models.user import User
from app.services.observability import snapshot
from app.services.workflow_governance import evaluate_workflow, run_rar_iteration

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


class IncidentOut(BaseModel):
    id: int
    run_id: int
    tenant_id: Optional[int] = None
    title: str
    severity: str
    status: str
    confidence: float
    consensus_score: float
    conflict_detected: bool
    evidence_json: dict
    recommendation_json: dict
    created_at: datetime
    updated_at: datetime


class ConsensusSummaryOut(BaseModel):
    incidents_total: int
    avg_consensus_score: float
    avg_confidence: float
    conflict_rate: float
    high_risk_open: int


class ExecutiveSummaryOut(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    run_id: Optional[int] = None
    summary_type: str
    title: str
    content: str
    xi_score: float
    metadata_json: dict
    created_at: datetime


class ReleaseDecisionOut(BaseModel):
    decision: str
    reason: str
    consensus_score: float
    confidence: float
    risk_level: str


class ChatMessage(BaseModel):
    role: str
    text: str

class AssistantAskBody(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    history: list[ChatMessage] = []


class AssistantAskOut(BaseModel):
    answer: str
    confidence: float
    evidence: dict


class RARIterationOut(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    incident_id: int
    iteration_index: int
    trigger_reason: str
    confidence_before: float
    confidence_after: float
    evidence_enrichment_json: dict
    created_at: datetime


class WorkflowRunOut(BaseModel):
    id: int
    tenant_id: Optional[int] = None
    incident_id: Optional[int] = None
    workflow_type: str
    status: str
    decision: Optional[str] = None
    score: float
    summary: str
    output_json: dict
    created_at: datetime


def _tenant_filter(current: User, field):
    if current.is_superadmin:
        return None
    return field == current.tenant_id


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(CorrelatedIncident).order_by(desc(CorrelatedIncident.created_at)).limit(limit)
    tenant_where = _tenant_filter(current, CorrelatedIncident.tenant_id)
    if tenant_where is not None:
        q = q.where(tenant_where)
    rows = db.execute(q).scalars().all()
    return [IncidentOut(**r.__dict__) for r in rows]


@router.get("/consensus/summary", response_model=ConsensusSummaryOut)
def get_consensus_summary(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(CorrelatedIncident)
    tenant_where = _tenant_filter(current, CorrelatedIncident.tenant_id)
    if tenant_where is not None:
        q = q.where(tenant_where)
    rows = db.execute(q).scalars().all()
    if not rows:
        return ConsensusSummaryOut(
            incidents_total=0, avg_consensus_score=0.0, avg_confidence=0.0, conflict_rate=0.0, high_risk_open=0
        )
    total = len(rows)
    avg_consensus = round(sum(float(r.consensus_score) for r in rows) / total, 4)
    avg_conf = round(sum(float(r.confidence) for r in rows) / total, 4)
    conflicts = sum(1 for r in rows if r.conflict_detected)
    high_risk_open = sum(1 for r in rows if r.status == "open" and r.severity in {"warning", "critical"})
    return ConsensusSummaryOut(
        incidents_total=total,
        avg_consensus_score=avg_consensus,
        avg_confidence=avg_conf,
        conflict_rate=round(conflicts / total, 4),
        high_risk_open=high_risk_open,
    )


@router.get("/executive-summaries", response_model=list[ExecutiveSummaryOut])
def list_executive_summaries(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(ExecutiveSummary).order_by(desc(ExecutiveSummary.created_at)).limit(limit)
    tenant_where = _tenant_filter(current, ExecutiveSummary.tenant_id)
    if tenant_where is not None:
        q = q.where(tenant_where)
    rows = db.execute(q).scalars().all()
    return [ExecutiveSummaryOut(**r.__dict__) for r in rows]


@router.get("/release-governance", response_model=ReleaseDecisionOut)
def get_release_governance_decision(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(CorrelatedIncident).order_by(desc(CorrelatedIncident.created_at)).limit(20)
    tenant_where = _tenant_filter(current, CorrelatedIncident.tenant_id)
    if tenant_where is not None:
        q = q.where(tenant_where)
    incidents = db.execute(q).scalars().all()
    if not incidents:
        return ReleaseDecisionOut(
            decision="go",
            reason="No correlated incidents detected",
            consensus_score=1.0,
            confidence=1.0,
            risk_level="low",
        )
    worst = max(incidents, key=lambda x: (x.severity == "critical", x.consensus_score))
    if worst.severity == "critical" and worst.confidence >= 0.55:
        return ReleaseDecisionOut(
            decision="no_go",
            reason=f"Critical incident detected: {worst.title}",
            consensus_score=round(float(worst.consensus_score), 4),
            confidence=round(float(worst.confidence), 4),
            risk_level="high",
        )
    return ReleaseDecisionOut(
        decision="go_with_guardrails",
        reason="No critical blocking incidents; monitor with guardrails",
        consensus_score=round(float(worst.consensus_score), 4),
        confidence=round(float(worst.confidence), 4),
        risk_level="medium",
    )


@router.post("/assistant/ask", response_model=AssistantAskOut)
def ask_ops_assistant(
    body: AssistantAskBody,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    question = body.question.lower()
    obs = snapshot(window_seconds=900)
    latest_run_q = select(GovernanceRun).order_by(desc(GovernanceRun.created_at)).limit(1)
    tenant_where = _tenant_filter(current, GovernanceRun.tenant_id)
    if tenant_where is not None:
        latest_run_q = latest_run_q.where(tenant_where)
    latest_run = db.execute(latest_run_q).scalars().first()
    latest = (latest_run.result_json or {}) if latest_run else {}
    signals = latest.get("integration_signals", {}) if isinstance(latest, dict) else {}

    if "cost" in question:
        aws = signals.get("aws", {})
        trend = aws.get("cost_trend", "unknown")
        answer = f"Recent cost trend appears '{trend}'. Check scale events and recent deployments for correlation."
        confidence = 0.66
    elif "latency" in question or "performance" in question:
        p95 = obs.get("latency_ms_p95", 0)
        err = obs.get("error_rate", 0.0)
        answer = f"Latency p95 is {p95}ms with error rate {err:.3f}. Prioritize endpoints with highest errors and recent deployment changes."
        confidence = 0.72
    elif "release" in question or "deploy" in question:
        gov = get_release_governance_decision(db=db, current=current)
        answer = f"Release recommendation: {gov.decision}. Reason: {gov.reason}."
        confidence = gov.confidence
    else:
        answer = "Cross-domain signals are available. Ask about release risk, latency spikes, security findings, or cost increases."
        confidence = 0.55

    return AssistantAskOut(
        answer=answer,
        confidence=round(float(confidence), 4),
        evidence={"observability": obs, "latest_integration_signals": signals},
    )


@router.post("/incidents/{incident_id}/rar", response_model=RARIterationOut)
def rerun_incident_with_rar(
    incident_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    incident = db.get(CorrelatedIncident, incident_id)
    if incident is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    if not current.is_superadmin and current.tenant_id != incident.tenant_id:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this incident")

    telemetry = snapshot(window_seconds=900)
    enriched = run_rar_iteration(incident.__dict__, telemetry)
    last_idx = (
        db.execute(
            select(RARIteration)
            .where(RARIteration.incident_id == incident.id)
            .order_by(desc(RARIteration.iteration_index))
            .limit(1)
        )
        .scalars()
        .first()
    )
    row = RARIteration(
        tenant_id=incident.tenant_id,
        incident_id=incident.id,
        iteration_index=(last_idx.iteration_index + 1) if last_idx else 1,
        trigger_reason=enriched["trigger_reason"],
        confidence_before=float(enriched["confidence_before"]),
        confidence_after=float(enriched["confidence_after"]),
        evidence_enrichment_json=enriched["evidence_enrichment_json"],
    )
    incident.confidence = row.confidence_after
    db.add(row)
    db.commit()
    db.refresh(row)
    return RARIterationOut(**row.__dict__)


@router.post("/workflows/{workflow_type}", response_model=WorkflowRunOut)
def run_governance_workflow(
    workflow_type: str,
    incident_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(CorrelatedIncident).order_by(desc(CorrelatedIncident.created_at)).limit(1)
    tenant_where = _tenant_filter(current, CorrelatedIncident.tenant_id)
    if tenant_where is not None:
        q = q.where(tenant_where)
    incident = db.get(CorrelatedIncident, incident_id) if incident_id else db.execute(q).scalars().first()
    if incident is None:
        # fall back to a synthetic placeholder incident context
        context = {
            "id": None,
            "severity": "warning",
            "confidence": 0.5,
            "consensus_score": 0.5,
            "title": "No incident context",
        }
        tenant_id = current.tenant_id
        ref_id = None
    else:
        if not current.is_superadmin and current.tenant_id != incident.tenant_id:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this incident")
        context = incident.__dict__
        tenant_id = incident.tenant_id
        ref_id = incident.id

    output = evaluate_workflow(workflow_type, context, snapshot(window_seconds=900))
    row = GovernanceWorkflowRun(
        tenant_id=tenant_id,
        incident_id=ref_id,
        workflow_type=output["workflow_type"],
        status=output["status"],
        decision=output["decision"],
        score=float(output["score"]),
        summary=output["summary"],
        output_json=output["output_json"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return WorkflowRunOut(**row.__dict__)


@router.get("/workflows", response_model=list[WorkflowRunOut])
def list_workflow_runs(
    workflow_type: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    q = select(GovernanceWorkflowRun).order_by(desc(GovernanceWorkflowRun.created_at)).limit(limit)
    tenant_where = _tenant_filter(current, GovernanceWorkflowRun.tenant_id)
    if tenant_where is not None:
        q = q.where(tenant_where)
    if workflow_type:
        q = q.where(GovernanceWorkflowRun.workflow_type == workflow_type.strip().lower())
    rows = db.execute(q).scalars().all()
    return [WorkflowRunOut(**r.__dict__) for r in rows]
