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
from app.models.governance import AuditEvent, GovernanceCase, GovernanceRun
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
