"""Apache Camel integration worker — executes routes from Kafka automation events."""

from __future__ import annotations

import logging
from typing import Any, Optional

from aaf.config import get_settings

_log = logging.getLogger("aaf.camel")


def execute_camel_route(action_type: str, payload: dict[str, Any], *, tenant_id: Optional[int]) -> dict[str, Any]:
    """
    Execute integration route for action_type.
    When integration_mode=camel, routes are defined under integrations/camel/*.camel.yaml.
    """
    settings = get_settings()
    route = action_type.replace("_", "-")
    _log.info("camel_route_execute", extra={"route": route, "tenant_id": tenant_id})

    if route in {"jira-blocker", "jira_blocker"}:
        return _route_jira_blocker(payload, tenant_id=tenant_id)
    if route in {"hold-release", "hold_release", "hold-release-workflow", "hold_release_workflow"}:
        return _route_hold_release(payload, tenant_id=tenant_id)

    return {"status": "ignored", "route": route}


def _route_jira_blocker(payload: dict[str, Any], *, tenant_id: Optional[int]) -> dict[str, Any]:
    """Route: Kafka automation.actions → Jira REST create issue."""
    from app import db as db_mod
    from app.models.governance import GovernanceRun
    from app.models.tenant import Tenant
    from app.services.action_executors.jira_blocker import execute_jira_blocker

    run_id = payload.get("run_id")
    action = str(payload.get("governance_action") or "hold_release")
    db = db_mod.SessionLocal()
    try:
        run = db.get(GovernanceRun, int(run_id)) if run_id else None
        tenant = db.get(Tenant, int(tenant_id)) if tenant_id else None
        return execute_jira_blocker(db, tenant=tenant, run=run, action=action, dry_run=bool(payload.get("dry_run")))
    finally:
        db.close()


def _route_hold_release(payload: dict[str, Any], *, tenant_id: Optional[int]) -> dict[str, Any]:
    """Route: hold event → portfolio webhook + notification channels."""
    from app import db as db_mod
    from app.models.governance import GovernanceRun
    from app.models.tenant import Tenant
    from app.services.action_executors.hold_release import execute_hold_release_workflow

    run_id = payload.get("run_id")
    db = db_mod.SessionLocal()
    try:
        run = db.get(GovernanceRun, int(run_id)) if run_id else None
        tenant = db.get(Tenant, int(tenant_id)) if tenant_id else None
        webhook_url = str(payload.get("hold_release_webhook_url") or "")
        return execute_hold_release_workflow(
            db,
            tenant_id=tenant.id if tenant else None,
            run=run,
            actor_user_id=int(payload.get("actor_user_id") or 0),
            webhook_url=webhook_url,
            dry_run=bool(payload.get("dry_run")),
        )
    finally:
        db.close()


def main() -> None:
    from app.consumers.kafka_worker import main as kafka_main

    kafka_main()


if __name__ == "__main__":
    main()
