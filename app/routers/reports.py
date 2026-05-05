"""Export/report endpoints for governance runs and audit events."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_permission
from app.models.governance import AuditEvent, GovernanceRun
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])


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


@router.get("/runs/summary")
def runs_summary(
    format: str = Query(default="json", pattern="^(json|csv)$"),
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("runs.create")),
):
    rows = db.execute(_scoped_runs_query(current).limit(limit)).scalars().all()
    payload = []
    for r in rows:
        result = r.result_json or {}
        consensus = (result.get("consensus") or {}).get("consensus_score")
        utility = (result.get("utility") or {}).get("recommended_action")
        payload.append(
            {
                "run_id": r.id,
                "tenant_id": r.tenant_id,
                "status": r.status,
                "prompt_id": r.prompt_id,
                "prompt": r.prompt,
                "consensus_score": consensus,
                "recommended_action": utility,
                "created_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
        )
    if format == "json":
        return {"count": len(payload), "items": payload}

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "run_id",
            "tenant_id",
            "status",
            "prompt_id",
            "prompt",
            "consensus_score",
            "recommended_action",
            "created_at",
            "finished_at",
        ],
    )
    writer.writeheader()
    for row in payload:
        writer.writerow(row)
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
