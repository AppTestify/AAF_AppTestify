"""Execute hold_release_workflow decision actions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.governance import AuditEvent, GovernanceRun, GovernanceWorkflowRun, ProjectRelease

_log = logging.getLogger(__name__)


def _consensus_from_run(run: GovernanceRun | None) -> float:
    if not run or not run.result_json:
        return 0.0
    orch = (run.result_json.get("decision_framing") or {}).get("orchestration") or run.result_json.get("orchestration") or {}
    try:
        return float(orch.get("consensus_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def execute_hold_release_workflow(
    db: Session,
    *,
    tenant_id: Optional[int],
    run: GovernanceRun | None,
    actor_user_id: int,
    webhook_url: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    consensus = _consensus_from_run(run)
    release_updates: list[dict[str, Any]] = []

    if run and run.portfolio_project_id:
        releases = (
            db.execute(
                select(ProjectRelease)
                .where(
                    ProjectRelease.project_id == run.portfolio_project_id,
                    ProjectRelease.tenant_id == tenant_id,
                    ProjectRelease.status.in_(("planned", "in_progress")),
                )
                .order_by(ProjectRelease.created_at.desc())
                .limit(1)
            )
            .scalars()
            .all()
        )
        for rel in releases:
            if not dry_run:
                rel.release_decision = "hold"
                rel.status = "on_hold"
                rel.consensus_score = consensus
                rel.run_id = run.id
            release_updates.append({"release_id": rel.id, "version": rel.version, "status": "on_hold"})

    workflow_row = None
    if not dry_run:
        workflow_row = GovernanceWorkflowRun(
            tenant_id=tenant_id,
            incident_id=None,
            workflow_type="hold_release",
            status="completed",
            decision="hold_release",
            score=consensus,
            summary=f"Hold-release workflow triggered for run #{run.id if run else 'n/a'}",
            output_json={
                "run_id": run.id if run else None,
                "release_updates": release_updates,
                "consensus_score": consensus,
            },
        )
        db.add(workflow_row)
        db.add(
            AuditEvent(
                tenant_id=tenant_id,
                actor_user_id=actor_user_id,
                area="automation",
                action="hold_release",
                entity_type="governance_run",
                entity_id=run.id if run else None,
                severity="warning",
                summary=f"Hold-release workflow executed for run #{run.id if run else 'n/a'}",
            )
        )

    webhook_status: Optional[int] = None
    if webhook_url and not dry_run:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    webhook_url,
                    json={
                        "event": "hold_release",
                        "run_id": run.id if run else None,
                        "consensus_score": consensus,
                        "release_updates": release_updates,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                webhook_status = resp.status_code
        except Exception:  # noqa: BLE001
            _log.exception("hold_release_webhook_failed")

    return {
        "workflow_type": "hold_release",
        "release_updates": release_updates,
        "workflow_run_id": workflow_row.id if workflow_row else None,
        "webhook_status": webhook_status,
        "dry_run": dry_run,
    }
