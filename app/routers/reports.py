"""Export/report endpoints for governance runs and audit events."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_permission
from app.models.governance import AuditEvent, GovernanceRun
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])

# Column order for empty CSV (no rows)
_RUN_SUMMARY_CSV_FIELDS = [
    "run_id",
    "tenant_id",
    "portfolio_project_id",
    "status",
    "prompt_id",
    "prompt",
    "orchestration_consensus_score",
    "findings_consensus_score",
    "findings_conflict_detected",
    "recommended_action",
    "utility_score",
    "xi_score",
    "rar_triggered",
    "rar_loops",
    "primary_recommendation_source",
    "created_at",
    "finished_at",
]


def _flatten_run_for_export(r: GovernanceRun) -> dict[str, Any]:
    """Normalized columns for CSV/JSON summaries (orchestration vs findings when present)."""
    result = r.result_json if isinstance(r.result_json, dict) else {}
    df = result.get("decision_framing") if isinstance(result.get("decision_framing"), dict) else {}
    orch = df.get("orchestration") if isinstance(df.get("orchestration"), dict) else {}
    fsyn = df.get("findings_synthesis") if isinstance(df.get("findings_synthesis"), dict) else {}
    consensus = result.get("consensus") if isinstance(result.get("consensus"), dict) else {}
    rar = result.get("rar") if isinstance(result.get("rar"), dict) else {}
    util = result.get("utility") if isinstance(result.get("utility"), dict) else {}
    xi = result.get("explainability") if isinstance(result.get("explainability"), dict) else {}

    orch_consensus = orch.get("consensus_score")
    if orch_consensus is None:
        orch_consensus = consensus.get("consensus_score")

    rec_action = orch.get("recommended_action") if orch else None
    if rec_action is None:
        rec_action = util.get("recommended_action")

    return {
        "run_id": r.id,
        "tenant_id": r.tenant_id,
        "portfolio_project_id": r.portfolio_project_id,
        "status": r.status,
        "prompt_id": r.prompt_id,
        "prompt": r.prompt,
        "orchestration_consensus_score": orch_consensus,
        "findings_consensus_score": fsyn.get("consensus_score"),
        "findings_conflict_detected": fsyn.get("conflict_detected"),
        "recommended_action": rec_action,
        "utility_score": orch.get("utility_score") if orch.get("utility_score") is not None else util.get("utility_score"),
        "xi_score": orch.get("xi_score") if orch.get("xi_score") is not None else xi.get("xi_score"),
        "rar_triggered": rar.get("rar_triggered"),
        "rar_loops": rar.get("rar_loops"),
        "primary_recommendation_source": df.get("primary_recommendation_source"),
        "created_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


def _executive_run_bundle(run: GovernanceRun) -> dict[str, Any]:
    """Shareable governance snapshot (tenant-scoped auth required)."""
    result = run.result_json if isinstance(run.result_json, dict) else {}
    return {
        "run_id": run.id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": run.tenant_id,
        "portfolio_project_id": run.portfolio_project_id,
        "prompt": run.prompt,
        "prompt_id": run.prompt_id,
        "status": run.status,
        "created_at": run.created_at.isoformat() if isinstance(run.created_at, datetime) else str(run.created_at),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "decision_framing": result.get("decision_framing"),
        "consensus": result.get("consensus"),
        "rar": result.get("rar"),
        "utility": result.get("utility"),
        "explainability": result.get("explainability"),
        "pm_view": result.get("pm_view"),
        "explanation": result.get("explanation"),
        "agentic_intelligence": result.get("agentic_intelligence"),
    }


def _scoped_runs_query(current: User):
    q = select(GovernanceRun).order_by(GovernanceRun.created_at.desc())
    if not current.is_superadmin:
        q = q.where(GovernanceRun.tenant_id == current.tenant_id)
    return q


def _scoped_audit_query(current: User):
    q = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if not current.is_superadmin:
        q = q.where(AuditEvent.tenant_id == current.tenant_id)
    return q


@router.get("/runs/{run_id}/export")
def export_single_run(
    run_id: int,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("runs.create")),
):
    """Download one run’s executive governance snapshot for sharing (auth required)."""
    row = db.get(GovernanceRun, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not current.is_superadmin and current.tenant_id != row.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")

    bundle = _executive_run_bundle(row)
    flat = _flatten_run_for_export(row)

    if format == "json":
        return {"format_version": 1, "summary_columns": flat, "executive_bundle": bundle}

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(flat.keys()))
    writer.writeheader()
    writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in flat.items()})
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="governance_run_{run_id}.csv"'},
    )


@router.get("/runs/summary")
def runs_summary(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    status: Optional[str] = Query(default=None),
    portfolio_project_id: Optional[int] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("runs.create")),
):
    q = _scoped_runs_query(current)
    if status:
        q = q.where(GovernanceRun.status == status)
    if portfolio_project_id is not None:
        q = q.where(GovernanceRun.portfolio_project_id == portfolio_project_id)
    rows = db.execute(q.limit(limit)).scalars().all()
    payload = [_flatten_run_for_export(r) for r in rows]
    if format == "json":
        return {"count": len(payload), "items": payload}

    buf = io.StringIO()
    fnames = list(payload[0].keys()) if payload else _RUN_SUMMARY_CSV_FIELDS
    writer = csv.DictWriter(buf, fieldnames=fnames)
    writer.writeheader()
    for row in payload:
        safe = {
            k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
            for k, v in row.items()
        }
        writer.writerow(safe)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="governance_run_summary.csv"'},
    )


@router.get("/audit-events")
def audit_events_export(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    area: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=10000),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    q = _scoped_audit_query(current)
    if area:
        q = q.where(AuditEvent.area == area)
    rows = db.execute(q.limit(limit)).scalars().all()
    payload = [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "actor_user_id": r.actor_user_id,
            "area": r.area,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "severity": r.severity,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
            "before_json": r.before_json,
            "after_json": r.after_json,
        }
        for r in rows
    ]
    if format == "json":
        return {"count": len(payload), "items": payload}

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "id",
            "tenant_id",
            "actor_user_id",
            "area",
            "action",
            "entity_type",
            "entity_id",
            "severity",
            "summary",
            "created_at",
            "before_json",
            "after_json",
        ],
    )
    writer.writeheader()
    for row in payload:
        row = row.copy()
        row["before_json"] = json.dumps(row["before_json"]) if row["before_json"] is not None else ""
        row["after_json"] = json.dumps(row["after_json"]) if row["after_json"] is not None else ""
        writer.writerow(row)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_events.csv"'},
    )
