"""Parallel connector evidence collection and package builder."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from aaf.config import Settings
from aaf.schema import EvidenceRecord
from connectors.evidence_normalizer import normalize_all
from connectors.azure_connector import AzureDevOpsConnector
from connectors.bitbucket_connector import BitbucketConnector
from connectors.finops_connector import FinopsConnector
from connectors.github_connector import GitHubConnector
from connectors.gitlab_connector import GitLabConnector
from connectors.jira_connector import JiraConnector
from connectors.pagerduty_connector import PagerDutyConnector
from tools.context import ToolContext, build_tool_context


async def _fetch_raw_evidence(
    settings: Settings,
    names: list[str],
    ctx: dict[str, str],
) -> dict[str, dict[str, Any]]:
    connector_map = {
        "github": GitHubConnector,
        "jira": JiraConnector,
        "finops": FinopsConnector,
        "gitlab": GitLabConnector,
        "bitbucket": BitbucketConnector,
        "pagerduty": PagerDutyConnector,
        "azure_devops": AzureDevOpsConnector,
    }
    
    active_names = [n for n in names if n in connector_map]
    tasks = [connector_map[name](settings).fetch_evidence(ctx) for name in active_names]  # type: ignore[arg-type]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    raw: dict[str, dict[str, Any]] = {}
    for name, res in zip(active_names, results):
        if not isinstance(res, Exception):
            raw[name] = res
        else:
            # Depending on strictness, we might want to log this or set an error dict
            raw[name] = {"error": str(res)}
            
    return raw


def _agent_tool_plans() -> dict[str, list[str]]:
    from agents import devops, devsecops, finops, pm_agent

    return {
        devops.DevOpsAgent.agent_id: [fn.__name__ for fn in devops.DevOpsAgent().tool_callables()],
        finops.FinOpsAgent.agent_id: [fn.__name__ for fn in finops.FinOpsAgent().tool_callables()],
        devsecops.DevSecOpsAgent.agent_id: [fn.__name__ for fn in devsecops.DevSecOpsAgent().tool_callables()],
        pm_agent.PMAgent.agent_id: [fn.__name__ for fn in pm_agent.PMAgent().tool_callables()],
    }


async def _warm_tool_cache(tool_ctx: ToolContext, tool_names: list[str]) -> dict[str, Any]:
    """Pre-run tools once so later agent loops read from the evidence package."""
    import importlib

    from agents.schemas import ToolResult
    from tools.context import cache_tool_result, get_cached_tool_result

    name_to_fn: dict[str, Any] = {}
    for names in _agent_tool_plans().values():
        for tool_name in names:
            if tool_name in name_to_fn:
                continue
            module_path = _tool_module_for_name(tool_name)
            if module_path is None:
                continue
            mod_name, fn_name = module_path
            try:
                mod = importlib.import_module(mod_name)
                fn = getattr(mod, fn_name, None)
                if fn is not None:
                    name_to_fn[tool_name] = fn
            except Exception:
                continue

    targets = tool_names or list(name_to_fn.keys())
    tools: dict[str, Any] = dict((tool_ctx.evidence_package or {}).get("tools") or {})

    async def _run_one(name: str) -> None:
        if name in tools or get_cached_tool_result(tool_ctx, name) is not None:
            return
        fn = name_to_fn.get(name)
        if fn is None:
            return
        try:
            result = await fn(tool_ctx)
            if isinstance(result, ToolResult):
                cache_tool_result(tool_ctx, result)
                tools[name] = result.model_dump(mode="json")
        except Exception:
            return

    await asyncio.gather(*[_run_one(name) for name in targets if name in name_to_fn])
    return tools


def _tool_module_for_name(tool_name: str) -> tuple[str, str] | None:
    mapping: dict[str, tuple[str, str]] = {
        "get_ci_status": ("tools.devops.ci_status", "get_ci_status"),
        "get_deploy_history": ("tools.devops.deploy_history", "get_deploy_history"),
        "detect_rollbacks": ("tools.devops.rollback_detector", "detect_rollbacks"),
        "check_branch_protection": ("tools.devops.branch_protection", "check_branch_protection"),
        "get_pr_status": ("tools.devops.pr_status", "get_pr_status"),
        "get_commit_activity": ("tools.devops.commit_activity", "get_commit_activity"),
        "check_pipeline_config": ("tools.devops.pipeline_config", "check_pipeline_config"),
        "count_blockers": ("tools.pm.blockers", "count_blockers"),
        "get_open_defects": ("tools.pm.open_defects", "get_open_defects"),
        "get_sprint_status": ("tools.pm.sprint_status", "get_sprint_status"),
        "get_spend_trend": ("tools.finops.spend_trend", "get_spend_trend"),
        "detect_scaling_anomaly": ("tools.finops.scaling_anomaly", "detect_scaling_anomaly"),
    }
    return mapping.get(tool_name)


async def collect_evidence(
    *,
    settings: Settings,
    prompt: str,
    connector_names: list[str],
    ctx: dict[str, str],
    tenant_ui_preferences: dict[str, Any] | None = None,
    warm_tools: bool = True,
) -> tuple[dict[str, Any], list[EvidenceRecord], dict[str, Any], ToolContext]:
    """Fetch connector payloads, normalize, build evidence package, and tool context."""
    raw = await _fetch_raw_evidence(settings, connector_names, ctx)
    fetched_at = datetime.now(timezone.utc).isoformat()
    for payload in raw.values():
        if isinstance(payload, dict):
            payload["_fetched_at"] = fetched_at

    normalized = normalize_all(raw)
    tool_extra: dict[str, Any] = {}
    if tenant_ui_preferences:
        tool_extra["ui_preferences"] = tenant_ui_preferences

    import uuid
    run_id = uuid.uuid4().hex
    staleness_summary = "Fresh"
    for payload in raw.values():
        if isinstance(payload, dict) and payload.get("is_stale", False):
            staleness_summary = "Contains stale data"
            break

    evidence_package: dict[str, Any] = {
        "prompt": prompt,
        "run_id": run_id,
        "signal_count": len(normalized),
        "staleness_summary": staleness_summary,
        "records": [r.model_dump(mode="json") for r in normalized],
        "raw_by_connector": raw,
        "fetched_at": fetched_at,
        "tools": {},
    }
    tool_ctx = build_tool_context(
        settings,
        github_repo=settings.github_repo,
        jira_project=settings.jira_project,
        jira_board_id=settings.jira_board_id,
        extra=tool_extra,
        evidence_package=evidence_package,
    )

    if warm_tools:
        await _warm_tool_cache(tool_ctx, [])
        evidence_package["tools"] = dict((tool_ctx.evidence_package or {}).get("tools") or {})

    return raw, normalized, evidence_package, tool_ctx
