"""Execute jira_blocker decision actions."""

from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy.orm import Session

from aaf.config import get_settings
from app.models.governance import GovernanceRun
from app.services.config_resolver import resolve_effective_settings
from app.models.tenant import Tenant
from tools.context import build_tool_context
from tools.pm.create_blocker import create_jira_blocker


def _run_summary(run: GovernanceRun | None, action: str) -> tuple[str, str]:
    consensus = ""
    if run and run.result_json:
        orch = (run.result_json.get("decision_framing") or {}).get("orchestration") or {}
        if not orch:
            orch = run.result_json.get("orchestration") or {}
        consensus = str(orch.get("consensus_score", ""))
    run_id = run.id if run else "n/a"
    summary = f"[Casantris] Governance {action.replace('_', ' ')} — run #{run_id}"
    description = (
        f"Automated governance blocker from Casantris.\n\n"
        f"Run ID: {run_id}\n"
        f"Action: {action}\n"
        f"Consensus: {consensus}\n"
        f"Prompt: {(run.prompt[:500] if run else '')}"
    )
    return summary, description


async def execute_jira_blocker_async(
    db: Session,
    *,
    tenant: Tenant | None,
    run: GovernanceRun | None,
    action: str,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {"key": "DRY-RUN", "url": "", "simulated": True, "dry_run": True}

    settings = resolve_effective_settings(db, get_settings(), tenant)
    summary, description = _run_summary(run, action)
    ctx = build_tool_context(
        settings,
        jira_project=getattr(settings, "jira_project", None),
        extra={"summary": summary, "description": description},
    )
    return await create_jira_blocker(ctx, summary=summary, description=description, labels=["release-blocker"])


def execute_jira_blocker(
    db: Session,
    *,
    tenant: Tenant | None,
    run: GovernanceRun | None,
    action: str,
    dry_run: bool,
) -> dict[str, Any]:
    return asyncio.run(execute_jira_blocker_async(db, tenant=tenant, run=run, action=action, dry_run=dry_run))
