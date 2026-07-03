"""Orchestrate execution of approved governance decisions."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.config import TenantSettings
from app.models.governance import AuditEvent, Decision, DecisionAction, GovernanceRun
from app.models.tenant import Tenant
from app.services.action_executors.hold_release import execute_hold_release_workflow
from app.services.action_executors.jira_blocker import execute_jira_blocker

_log = logging.getLogger(__name__)

ACTIONS_BY_GOVERNANCE: dict[str, list[str]] = {
    "hold_release": ["jira_blocker", "hold_release_workflow"],
    "patch_block_release": ["jira_blocker"],
}

DEFAULT_AUTOMATION_CONFIG: dict[str, Any] = {
    "enabled": False,
    "dry_run": False,
    "require_approval": True,
    "jira_blocker_enabled": True,
    "hold_release_workflow_enabled": True,
    "hold_release_webhook_url": "",
}


def get_automation_config(settings_row: TenantSettings | None) -> dict[str, Any]:
    prefs = (settings_row.ui_preferences if settings_row else {}) or {}
    raw = prefs.get("action_automation") or {}
    merged = {**DEFAULT_AUTOMATION_CONFIG, **raw}
    return merged


def _action_enabled(config: dict[str, Any], action_type: str) -> bool:
    if action_type == "jira_blocker":
        return bool(config.get("jira_blocker_enabled", True))
    if action_type == "hold_release_workflow":
        return bool(config.get("hold_release_workflow_enabled", True))
    return True


def _resolve_governance_action(decision: Decision | None, run: GovernanceRun | None) -> str:
    if decision:
        action = (decision.final_action or decision.recommended_action or "").strip().lower()
        if action:
            return action
    if run and run.result_json:
        orch = (run.result_json.get("decision_framing") or {}).get("orchestration") or run.result_json.get("orchestration") or {}
        return str(orch.get("recommended_action", "")).strip().lower()
    return ""


def _execute_single(
    db: Session,
    *,
    action_row: DecisionAction,
    tenant: Tenant | None,
    run: GovernanceRun | None,
    governance_action: str,
    config: dict[str, Any],
    actor_user_id: int,
) -> None:
    action_row.state = "running"
    db.flush()
    dry_run = bool(config.get("dry_run"))
    try:
        if action_row.action_type == "jira_blocker":
            result = execute_jira_blocker(
                db,
                tenant=tenant,
                run=run,
                action=governance_action,
                dry_run=dry_run,
            )
        elif action_row.action_type == "hold_release_workflow":
            result = execute_hold_release_workflow(
                db,
                tenant_id=tenant.id if tenant else None,
                run=run,
                actor_user_id=actor_user_id,
                webhook_url=str(config.get("hold_release_webhook_url") or ""),
                dry_run=dry_run,
            )
        else:
            raise ValueError(f"Unknown action type: {action_row.action_type}")
        action_row.state = "simulated" if dry_run else "succeeded"
        action_row.result_json = result
    except Exception as exc:  # noqa: BLE001
        _log.exception("action_execution_failed", extra={"action_type": action_row.action_type})
        action_row.state = "failed"
        action_row.result_json = {"error": str(exc)}
    action_row.finished_at = datetime.now(timezone.utc)


def queue_decision_actions(
    db: Session,
    *,
    decision: Decision,
    tenant: Tenant | None,
    settings_row: TenantSettings | None,
    actor_user_id: int,
    run: GovernanceRun | None = None,
) -> list[DecisionAction]:
    config = get_automation_config(settings_row)
    if not config.get("enabled"):
        return []

    governance_action = _resolve_governance_action(decision, run)
    action_types = ACTIONS_BY_GOVERNANCE.get(governance_action, [])
    if not action_types:
        return []

    if run is None and decision.run_id:
        run = db.get(GovernanceRun, decision.run_id)

    created: list[DecisionAction] = []
    for action_type in action_types:
        if not _action_enabled(config, action_type):
            continue
        row = DecisionAction(
            decision_id=decision.id,
            action_type=action_type,
            state="pending",
            payload_json={
                "governance_action": governance_action,
                "run_id": run.id if run else None,
                "dry_run": bool(config.get("dry_run")),
            },
        )
        db.add(row)
        created.append(row)

    db.flush()
    from aaf.config import get_settings
    from app.services.kafka_producer import kafka_enabled, publish_automation_action

    settings = get_settings()
    use_camel = settings.integration_mode.lower() == "camel" and kafka_enabled()

    for row in created:
        if use_camel:
            row.state = "queued"
            publish_automation_action(
                tenant_id=tenant.id if tenant else None,
                action_type=row.action_type,
                decision_id=decision.id,
                run_id=run.id if run else None,
                payload={
                    "governance_action": governance_action,
                    "dry_run": bool(config.get("dry_run")),
                    "hold_release_webhook_url": str(config.get("hold_release_webhook_url") or ""),
                },
            )
            continue
        _execute_single(
            db,
            action_row=row,
            tenant=tenant,
            run=run,
            governance_action=governance_action,
            config=config,
            actor_user_id=actor_user_id,
        )

    db.add(
        AuditEvent(
            tenant_id=tenant.id if tenant else None,
            actor_user_id=actor_user_id,
            area="automation",
            action="executed",
            entity_type="decision",
            entity_id=decision.id,
            summary=f"Executed {len(created)} automation action(s) for decision {decision.id}",
        )
    )
    return created


def queue_run_actions(
    db: Session,
    *,
    run: GovernanceRun,
    tenant: Tenant | None,
    settings_row: TenantSettings | None,
    actor_user_id: int,
) -> list[DecisionAction]:
    """Execute actions directly from a run (no decision record)."""
    config = get_automation_config(settings_row)
    if not config.get("enabled"):
        return []

    governance_action = _resolve_governance_action(None, run)
    action_types = ACTIONS_BY_GOVERNANCE.get(governance_action, [])
    if not action_types:
        return []

    # Synthetic decision_id=0 actions stored with run id in payload only — use negative sentinel
    # Instead create ephemeral DecisionAction rows linked to a lightweight decision if needed.
    # For run-only path, execute without persisting decision_id — use decision_id from run's latest decision or 0.
    from sqlalchemy import select

    from app.models.governance import Decision as DecisionModel, GovernanceCase

    decision = db.execute(
        select(DecisionModel).where(DecisionModel.run_id == run.id).order_by(DecisionModel.created_at.desc()).limit(1)
    ).scalar_one_or_none()
    if decision is None:
        case = db.execute(
            select(GovernanceCase)
            .where(GovernanceCase.tenant_id == run.tenant_id)
            .order_by(GovernanceCase.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if case is None:
            case = GovernanceCase(
                tenant_id=run.tenant_id,
                title=f"Automation case for run #{run.id}",
                status="open",
                latest_run_id=run.id,
                portfolio_project_id=run.portfolio_project_id,
                created_by_user_id=actor_user_id,
            )
            db.add(case)
            db.flush()
        decision = DecisionModel(
            case_id=case.id,
            run_id=run.id,
            status="approved",
            recommended_action=governance_action,
            final_action=governance_action,
            rationale="Auto-created for run action execution",
            created_by_user_id=actor_user_id,
            approved_by_user_id=actor_user_id,
            approved_at=datetime.now(timezone.utc),
        )
        db.add(decision)
        db.flush()

    return queue_decision_actions(
        db,
        decision=decision,
        tenant=tenant,
        settings_row=settings_row,
        actor_user_id=actor_user_id,
        run=run,
    )
