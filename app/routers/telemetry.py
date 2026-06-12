"""Dashboard and integrations telemetry APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user
from app.models.config import TenantAIProviderConfig, TenantConnectorConfig
from app.models.governance import AuditEvent, Decision, EvidenceSnapshot, GovernanceCase, GovernanceRun
from app.models.user import User
from app.services.observability import render_prometheus, snapshot

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


class DashboardSummaryOut(BaseModel):
    runs_total: int
    runs_24h: int
    runs_success_24h: int
    cases_open: int
    cases_total: int
    alerts_24h: int
    connectors_enabled: int
    connectors_total: int
    providers_enabled: int
    providers_total: int
    run_status_counts: dict[str, int]
    case_status_counts: dict[str, int]
    recent_runs: list[dict]
    recent_alerts: list[dict]
    connector_health: list[dict]
    provider_health: list[dict]
    integration_coverage_pct: float
    integration_fresh_pct: float


class ObservabilitySummaryOut(BaseModel):
    window_seconds: int
    uptime_seconds: int
    requests_total: int
    requests_per_min: float
    error_rate: float
    latency_ms_p50: float
    latency_ms_p95: float
    latency_ms_p99: float
    inflight_requests: int
    run_queue_depth: int
    runs_total: int
    runs_succeeded: int
    runs_failed: int
    runs_retried: int
    run_latency_ms_p95: float
    endpoints_top: list[dict]
    slo_burn_rate: dict
    alert_rules: list[dict]
    spans_recent: list[dict]
    connector_calls_total: int
    connector_error_rate: float
    connector_latency_ms_p95: float
    connector_status_counts: dict
    connector_error_categories: dict
    failure_recovery: dict
    llm_invocation: dict


class DecisionLifecycleOut(BaseModel):
    connectors: dict
    telemetry: dict
    governance: dict
    release: dict
    defendability: dict


class RunsTimeseriesDayPoint(BaseModel):
    date: str
    counts: dict[str, int]


class RunsTimeseriesOut(BaseModel):
    days: int
    series: list[RunsTimeseriesDayPoint]


def _tenant_scope(where_col, current: User):
    if current.is_superadmin:
        return None
    return where_col == current.tenant_id


@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    run_scope = _tenant_scope(GovernanceRun.tenant_id, current)
    case_scope = _tenant_scope(GovernanceCase.tenant_id, current)
    audit_scope = _tenant_scope(AuditEvent.tenant_id, current)
    connector_scope = _tenant_scope(TenantConnectorConfig.tenant_id, current)
    provider_scope = _tenant_scope(TenantAIProviderConfig.tenant_id, current)

    runs_total_q = select(func.count(GovernanceRun.id))
    runs_24h_q = select(func.count(GovernanceRun.id)).where(GovernanceRun.created_at >= since)
    runs_success_24h_q = select(func.count(GovernanceRun.id)).where(
        GovernanceRun.created_at >= since, GovernanceRun.status == "succeeded"
    )
    if run_scope is not None:
        runs_total_q = runs_total_q.where(run_scope)
        runs_24h_q = runs_24h_q.where(run_scope)
        runs_success_24h_q = runs_success_24h_q.where(run_scope)

    cases_total_q = select(func.count(GovernanceCase.id))
    cases_open_q = select(func.count(GovernanceCase.id)).where(GovernanceCase.status.in_(["new", "in_review"]))
    if case_scope is not None:
        cases_total_q = cases_total_q.where(case_scope)
        cases_open_q = cases_open_q.where(case_scope)

    alerts_24h_q = select(func.count(AuditEvent.id)).where(AuditEvent.created_at >= since)
    if audit_scope is not None:
        alerts_24h_q = alerts_24h_q.where(audit_scope)

    connectors_q = select(func.sum(case((TenantConnectorConfig.enabled.is_(True), 1), else_=0)), func.count(TenantConnectorConfig.id))
    if connector_scope is not None:
        connectors_q = connectors_q.where(connector_scope)

    providers_q = select(func.sum(case((TenantAIProviderConfig.enabled.is_(True), 1), else_=0)), func.count(TenantAIProviderConfig.id))
    if provider_scope is not None:
        providers_q = providers_q.where(provider_scope)

    runs_total = int(db.scalar(runs_total_q) or 0)
    runs_24h = int(db.scalar(runs_24h_q) or 0)
    runs_success_24h = int(db.scalar(runs_success_24h_q) or 0)
    cases_total = int(db.scalar(cases_total_q) or 0)
    cases_open = int(db.scalar(cases_open_q) or 0)
    alerts_24h = int(db.scalar(alerts_24h_q) or 0)

    connectors_enabled, connectors_total = db.execute(connectors_q).one()
    providers_enabled, providers_total = db.execute(providers_q).one()

    run_status_q = select(GovernanceRun.status, func.count(GovernanceRun.id)).group_by(GovernanceRun.status)
    if run_scope is not None:
        run_status_q = run_status_q.where(run_scope)
    run_status_counts = {status: int(count) for status, count in db.execute(run_status_q).all()}

    case_status_q = select(GovernanceCase.status, func.count(GovernanceCase.id)).group_by(GovernanceCase.status)
    if case_scope is not None:
        case_status_q = case_status_q.where(case_scope)
    case_status_counts = {status: int(count) for status, count in db.execute(case_status_q).all()}

    recent_runs_q = (
        select(GovernanceRun)
        .order_by(GovernanceRun.created_at.desc())
        .limit(8)
    )
    if run_scope is not None:
        recent_runs_q = recent_runs_q.where(run_scope)
    recent_runs = [
        {
            "id": r.id,
            "status": r.status,
            "prompt": r.prompt[:120],
            "created_at": r.created_at,
        }
        for r in db.execute(recent_runs_q).scalars().all()
    ]

    recent_alerts_q = (
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(8)
    )
    if audit_scope is not None:
        recent_alerts_q = recent_alerts_q.where(audit_scope)
    recent_alerts = [
        {
            "id": e.id,
            "area": e.area,
            "action": e.action,
            "severity": e.severity,
            "summary": e.summary,
            "created_at": e.created_at,
        }
        for e in db.execute(recent_alerts_q).scalars().all()
    ]

    connector_health_q = select(TenantConnectorConfig).order_by(TenantConnectorConfig.connector_name.asc())
    if connector_scope is not None:
        connector_health_q = connector_health_q.where(connector_scope)
    connector_health = [
        {
            "connector_name": c.connector_name,
            "enabled": c.enabled,
            "last_validation_ok": c.last_validation_ok,
            "last_validation_error": c.last_validation_error,
            "last_validated_at": c.last_validated_at,
        }
        for c in db.execute(connector_health_q).scalars().all()
    ]
    integration_coverage_pct = (
        round((sum(1 for c in connector_health if c["enabled"]) / len(connector_health)) * 100, 2) if connector_health else 0.0
    )
    integration_fresh_pct = (
        round((sum(1 for c in connector_health if c.get("last_sync_at")) / len(connector_health)) * 100, 2)
        if connector_health
        else 0.0
    )

    provider_health_q = select(TenantAIProviderConfig).order_by(TenantAIProviderConfig.provider_name.asc())
    if provider_scope is not None:
        provider_health_q = provider_health_q.where(provider_scope)
    provider_health = [
        {
            "provider_name": p.provider_name,
            "enabled": p.enabled,
            "last_validation_ok": p.last_validation_ok,
            "last_validation_error": p.last_validation_error,
            "last_validated_at": p.last_validated_at,
        }
        for p in db.execute(provider_health_q).scalars().all()
    ]

    return DashboardSummaryOut(
        runs_total=runs_total,
        runs_24h=runs_24h,
        runs_success_24h=runs_success_24h,
        cases_open=cases_open,
        cases_total=cases_total,
        alerts_24h=alerts_24h,
        connectors_enabled=int(connectors_enabled or 0),
        connectors_total=int(connectors_total or 0),
        providers_enabled=int(providers_enabled or 0),
        providers_total=int(providers_total or 0),
        run_status_counts=run_status_counts,
        case_status_counts=case_status_counts,
        recent_runs=recent_runs,
        recent_alerts=recent_alerts,
        connector_health=connector_health,
        provider_health=provider_health,
        integration_coverage_pct=integration_coverage_pct,
        integration_fresh_pct=integration_fresh_pct,
    )


@router.get("/runs-timeseries", response_model=RunsTimeseriesOut)
def get_runs_timeseries(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    run_scope = _tenant_scope(GovernanceRun.tenant_id, current)
    day_expr = func.date(GovernanceRun.created_at)
    ts_q = (
        select(day_expr, GovernanceRun.status, func.count(GovernanceRun.id))
        .where(GovernanceRun.created_at >= since)
        .group_by(day_expr, GovernanceRun.status)
    )
    if run_scope is not None:
        ts_q = ts_q.where(run_scope)

    day_counts: dict[str, dict[str, int]] = {}
    for day, status, count in db.execute(ts_q).all():
        day_str = str(day)
        day_counts.setdefault(day_str, {})[status] = int(count)

    series: list[RunsTimeseriesDayPoint] = []
    for i in range(days):
        d = (since + timedelta(days=i)).date().isoformat()
        series.append(RunsTimeseriesDayPoint(date=d, counts=day_counts.get(d, {})))

    return RunsTimeseriesOut(days=days, series=series)


@router.get("/observability/summary", response_model=ObservabilitySummaryOut)
def get_observability_summary(
    window_seconds: int = Query(default=300, ge=60, le=3600),
    _current: User = Depends(get_current_active_user),
):
    return ObservabilitySummaryOut(**snapshot(window_seconds=window_seconds))


@router.get("/observability/metrics", response_class=PlainTextResponse)
def get_prometheus_metrics(
    window_seconds: int = Query(default=300, ge=60, le=3600),
    _current: User = Depends(get_current_active_user),
):
    return PlainTextResponse(render_prometheus(window_seconds=window_seconds), media_type="text/plain; version=0.0.4")


@router.get("/decision-lifecycle", response_model=DecisionLifecycleOut)
def get_decision_lifecycle(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_active_user),
):
    run_scope = _tenant_scope(GovernanceRun.tenant_id, current)
    case_scope = _tenant_scope(GovernanceCase.tenant_id, current)
    audit_scope = _tenant_scope(AuditEvent.tenant_id, current)
    connector_scope = _tenant_scope(TenantConnectorConfig.tenant_id, current)

    runs_q = select(func.count(GovernanceRun.id), func.sum(case((GovernanceRun.status == "succeeded", 1), else_=0)))
    cases_q = select(
        func.count(GovernanceCase.id),
        func.sum(case((GovernanceCase.status.in_(["new", "in_review"]), 1), else_=0)),
    )
    decisions_q = select(
        func.count(Decision.id),
        func.sum(case((Decision.status == "approved", 1), else_=0)),
    ).select_from(Decision).join(GovernanceCase, GovernanceCase.id == Decision.case_id)
    evidence_q = select(func.count(EvidenceSnapshot.id)).select_from(EvidenceSnapshot).join(
        GovernanceRun, GovernanceRun.id == EvidenceSnapshot.run_id
    )
    audits_q = select(func.count(AuditEvent.id)).where(AuditEvent.area.in_(["governance_run", "governance_case", "decision", "alerts"]))
    connectors_q = select(TenantConnectorConfig).order_by(TenantConnectorConfig.connector_name.asc())

    if run_scope is not None:
        runs_q = runs_q.where(run_scope)
        evidence_q = evidence_q.where(run_scope)
    if case_scope is not None:
        cases_q = cases_q.where(case_scope)
        decisions_q = decisions_q.where(case_scope)
    if audit_scope is not None:
        audits_q = audits_q.where(audit_scope)
    if connector_scope is not None:
        connectors_q = connectors_q.where(connector_scope)

    runs_total, runs_succeeded = db.execute(runs_q).one()
    cases_total, cases_open = db.execute(cases_q).one()
    decisions_total, decisions_approved = db.execute(decisions_q).one()
    evidence_total = int(db.scalar(evidence_q) or 0)
    audit_total = int(db.scalar(audits_q) or 0)

    connector_rows = db.execute(connectors_q).scalars().all()
    connector_payload = {r.connector_name: (r.telemetry_json or {}) for r in connector_rows}
    github = connector_payload.get("github", {})
    jira = connector_payload.get("jira", {})
    azure = connector_payload.get("azure", {})

    obs = snapshot(window_seconds=900)
    release_signals = {
        "github_success_rate": float(github.get("success_rate") or 0.0),
        "github_failing_checks": int(github.get("failing_checks") or 0),
        "jira_blocked_tickets": int(jira.get("blocked_tickets") or 0),
        "azure_release_readiness": str(azure.get("release_readiness") or "unknown"),
        "azure_build_success_rate": float(azure.get("build_success_rate") or 0.0),
    }
    release_confidence = 0.0
    if release_signals["github_success_rate"] > 0:
        release_confidence += 0.4 * release_signals["github_success_rate"]
    if release_signals["azure_build_success_rate"] > 0:
        release_confidence += 0.4 * release_signals["azure_build_success_rate"]
    if release_signals["jira_blocked_tickets"] == 0:
        release_confidence += 0.2
    release_confidence = round(min(1.0, release_confidence), 3)

    outcome_traceability = round(
        min(
            1.0,
            (
                (int(decisions_approved or 0) / max(1, int(decisions_total or 0))) * 0.45
                + (evidence_total / max(1, int(runs_total or 0))) * 0.25
                + (audit_total / max(1, int(runs_total or 0))) * 0.3
            ),
        ),
        3,
    )

    return DecisionLifecycleOut(
        connectors={
            "github": github,
            "jira": jira,
            "azure": azure,
            "coverage_total": len(connector_rows),
            "fresh_connectors": sum(1 for r in connector_rows if (r.telemetry_json or {}).get("freshness") == "fresh"),
        },
        telemetry={
            "requests_per_min": obs.get("requests_per_min", 0),
            "error_rate": obs.get("error_rate", 0),
            "latency_ms_p95": obs.get("latency_ms_p95", 0),
            "slo_state": (obs.get("slo_burn_rate") or {}).get("state", "unknown"),
            "connector_error_rate": obs.get("connector_error_rate", 0),
        },
        governance={
            "runs_total": int(runs_total or 0),
            "runs_succeeded": int(runs_succeeded or 0),
            "cases_total": int(cases_total or 0),
            "cases_open": int(cases_open or 0),
            "decisions_total": int(decisions_total or 0),
            "decisions_approved": int(decisions_approved or 0),
            "evidence_total": evidence_total,
            "audit_events_total": audit_total,
        },
        release={
            **release_signals,
            "release_confidence": release_confidence,
            "status": "go" if release_confidence >= 0.75 else "review",
        },
        defendability={
            "outcome_traceability_score": outcome_traceability,
            "defendable": outcome_traceability >= 0.7 and release_confidence >= 0.75,
            "explainability_basis": [
                "connector telemetry",
                "governance decisions",
                "audit events",
                "evidence snapshots",
            ],
        },
    )
