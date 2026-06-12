"""Map MCP JSON payloads to ToolResult raw_signals per AgileOps tool."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from agents.schemas import ToolResult


def _as_list(payload: Any, *keys: str) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in keys:
        val = payload.get(key)
        if isinstance(val, list):
            return val
    return []


def _normalize_get_ci_status(payload: Any, ctx: Any) -> dict[str, Any]:
    runs = _as_list(payload, "workflow_runs", "runs", "items")
    total = max(1, len(runs))
    success = sum(1 for r in runs if str(r.get("conclusion", "")).lower() == "success")
    failed = [r for r in runs if str(r.get("conclusion", "")).lower() == "failure"]
    return {
        "ci_pass_rate": round(success / total, 4),
        "failed_steps": ["other"] if failed else [],
        "blocking_check": bool(failed),
        "runs_in_window": len(runs),
    }


def _normalize_get_deploy_history(payload: Any, ctx: Any) -> dict[str, Any]:
    deployments = _as_list(payload, "deployments", "items")
    return {
        "deploy_freq": len(deployments),
        "change_fail_rate": 0.0,
        "last_env": deployments[0].get("environment") if deployments else None,
        "tag_present": False,
        "mttr_hours": None,
    }


def _normalize_check_branch_protection(payload: Any, ctx: Any) -> dict[str, Any]:
    prot = payload if isinstance(payload, dict) else {}
    return {
        "reviews_met": bool(prot.get("required_pull_request_reviews") or prot.get("reviews_met")),
        "checks_pass": True,
        "pr_merged": False,
        "signed_commits": bool(prot.get("required_signatures") or prot.get("signed_commits")),
    }


def _normalize_get_pr_status(payload: Any, ctx: Any) -> dict[str, Any]:
    pulls = _as_list(payload, "pulls", "items")
    return {
        "open_pr_count": len(pulls),
        "approved_count": 0,
        "changes_requested_count": 0,
        "draft_pr_flag": any(p.get("draft") for p in pulls),
        "oldest_open_pr_days": 0,
    }


def _normalize_get_sprint_status(payload: Any, ctx: Any) -> dict[str, Any]:
    sprint = payload.get("sprint") if isinstance(payload, dict) else {}
    if not sprint and isinstance(payload, dict):
        sprint = payload
    issues = _as_list(payload, "issues", "values")
    done = sum(
        1
        for i in issues
        if str((i.get("fields") or {}).get("status", {}).get("name", "")).lower() in {"done", "closed"}
    )
    total = max(1, len(issues))
    return {
        "sprint_done_pct": round((done / total) * 100.0, 1),
        "days_remaining": 7,
        "stories_remaining": total - done,
        "sprint_name": sprint.get("name"),
    }


def _normalize_count_blockers(payload: Any, ctx: Any) -> dict[str, Any]:
    issues = _as_list(payload, "issues", "values")
    keys = [str(i.get("key", "")) for i in issues]
    return {
        "blocked_count": len(issues),
        "story_keys": keys,
        "blocker_reasons": [str((i.get("fields") or {}).get("summary", ""))[:80] for i in issues],
    }


def _normalize_get_open_defects(payload: Any, ctx: Any) -> dict[str, Any]:
    issues = _as_list(payload, "issues", "values")
    return {
        "open_bugs_high": len(issues),
        "oldest_defect_age_days": 0.0,
        "defect_keys": [str(i.get("key", "")) for i in issues],
    }


def _normalize_scan_cves(payload: Any, ctx: Any) -> dict[str, Any]:
    alerts = _as_list(payload, "alerts", "code_scanning_alerts")
    critical = sum(1 for a in alerts if str(a.get("rule", {}).get("severity", a.get("severity", ""))).lower() == "critical")
    high = sum(1 for a in alerts if str(a.get("rule", {}).get("severity", a.get("severity", ""))).lower() == "high")
    return {
        "critical_count": critical,
        "high_count": high,
        "affected_packages": [],
    }


def _normalize_scan_secrets(payload: Any, ctx: Any) -> dict[str, Any]:
    alerts = _as_list(payload, "alerts", "secret_scanning_alerts")
    open_alerts = [a for a in alerts if str(a.get("state", "open")).lower() == "open"]
    return {
        "secrets_detected": bool(open_alerts),
        "affected_files": [str(a.get("location", {}).get("path", "")) for a in open_alerts[:5]],
    }


NORMALIZERS: dict[str, Callable[[Any, Any], dict[str, Any]]] = {
    "get_ci_status": _normalize_get_ci_status,
    "get_deploy_history": _normalize_get_deploy_history,
    "check_branch_protection": _normalize_check_branch_protection,
    "get_pr_status": _normalize_get_pr_status,
    "get_sprint_status": _normalize_get_sprint_status,
    "count_blockers": _normalize_count_blockers,
    "get_open_defects": _normalize_get_open_defects,
    "scan_cves": _normalize_scan_cves,
    "scan_secrets": _normalize_scan_secrets,
}


def build_tool_result_from_mcp(
    agileops_tool: str,
    payload: Any,
    ctx: Any,
    *,
    signal: float | None = None,
) -> ToolResult | None:
    normalizer = NORMALIZERS.get(agileops_tool)
    if normalizer is None:
        return None
    raw = normalizer(payload, ctx)
    raw["transport"] = "mcp"
    risk = signal if signal is not None else min(1.0, max(0.05, float(raw.get("blocking_check", 0) or raw.get("critical_count", 0) * 0.5)))
    if agileops_tool == "scan_secrets" and raw.get("secrets_detected"):
        risk = 0.98
    if agileops_tool == "scan_cves" and int(raw.get("critical_count", 0)) > 0:
        risk = 0.92
    return ToolResult(
        tool_name=agileops_tool,
        signal=round(risk, 4),
        captured_at=datetime.now(timezone.utc),
        raw_signals=raw,
        evidence_lines=[f"{agileops_tool} via MCP"],
    )
