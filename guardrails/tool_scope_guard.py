"""Tool scope guardrail — agent allowlist and write-operation blocks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from guardrails.types import GuardrailResult, GuardrailViolation

if TYPE_CHECKING:
    from aaf.config import Settings

AGENT_TOOL_ALLOWLIST: dict[str, frozenset[str]] = {
    "devops": frozenset(
        {"get_ci_status", "get_deploy_history", "detect_rollbacks", "check_branch_protection"}
    ),
    "finops": frozenset(
        {
            "get_spend_trend",
            "check_budget_pace",
            "detect_scaling_anomaly",
            "calc_unit_cost",
            "get_ri_coverage",
        }
    ),
    "devsecops": frozenset(
        {"scan_cves", "scan_secrets", "check_policy_violations", "audit_dependencies"}
    ),
    "project_management": frozenset(
        {
            "get_sprint_status",
            "count_blockers",
            "get_open_defects",
            "calc_velocity_risk",
            "check_latency",
            "check_error_rate",
            "check_queue_depth",
        }
    ),
}

_WRITE_TOOL_PREFIXES = ("create_", "delete_", "update_", "post_", "put_", "patch_", "mutate_")


def append_tool_scope_event(raw_signals: dict, *, tool_name: str, message: str) -> dict:
    """Append a tool_scope_guard event to agent raw_signals for audit/UI."""
    events = list(raw_signals.get("guardrail_events") or [])
    events.append({"guard": "tool_scope_guard", "tool_name": tool_name, "message": message})
    return {**raw_signals, "guardrail_events": events}


def check_tool_call(
    agent_id: str,
    tool_name: str,
    *,
    call_index: int = 0,
    settings: Optional[Settings] = None,
) -> GuardrailResult:
    """Validate a single tool invocation for an agent."""
    from aaf.config import Settings as SettingsCls

    cfg = settings or SettingsCls()
    violations: list[GuardrailViolation] = []
    blocked = False

    if not cfg.guardrails_enabled:
        return GuardrailResult(guard_name="tool_scope_guard", passed=True, violations=[])

    allowlist = AGENT_TOOL_ALLOWLIST.get(agent_id)
    if allowlist is not None and tool_name not in allowlist:
        violations.append(
            GuardrailViolation(
                rule="tool_not_allowed",
                severity="block",
                message=f"Tool '{tool_name}' is not in allowlist for agent '{agent_id}'",
            )
        )
        blocked = True

    if any(tool_name.startswith(prefix) for prefix in _WRITE_TOOL_PREFIXES):
        violations.append(
            GuardrailViolation(
                rule="write_tool_blocked",
                severity="block",
                message=f"Mutating tool '{tool_name}' is not permitted in governance runs",
            )
        )
        blocked = True

    max_calls = cfg.max_tool_calls_per_agent
    if call_index >= max_calls:
        violations.append(
            GuardrailViolation(
                rule="tool_call_budget",
                severity="block",
                message=f"Agent '{agent_id}' exceeded max tool calls ({max_calls})",
            )
        )
        blocked = True

    return GuardrailResult(
        guard_name="tool_scope_guard",
        passed=not blocked,
        blocked=blocked,
        violations=violations,
        metadata={"agent_id": agent_id, "tool_name": tool_name, "call_index": str(call_index)},
    )


def validate_agent_tool_plan(
    agent_id: str,
    tool_names: list[str],
    settings: Optional[Settings] = None,
) -> GuardrailResult:
    """Validate the full static tool plan for an agent before execution."""
    from aaf.config import Settings as SettingsCls

    cfg = settings or SettingsCls()
    violations: list[GuardrailViolation] = []
    blocked = False
    if not cfg.guardrails_enabled:
        return GuardrailResult(guard_name="tool_scope_guard", passed=True, violations=[])

    allowlist = AGENT_TOOL_ALLOWLIST.get(agent_id)
    for name in tool_names:
        if allowlist is not None and name not in allowlist:
            violations.append(
                GuardrailViolation(
                    rule="tool_not_allowed",
                    severity="block",
                    message=f"Tool '{name}' is not in allowlist for agent '{agent_id}'",
                )
            )
            blocked = True
        if any(name.startswith(prefix) for prefix in _WRITE_TOOL_PREFIXES):
            violations.append(
                GuardrailViolation(
                    rule="write_tool_blocked",
                    severity="block",
                    message=f"Mutating tool '{name}' is not permitted in governance runs",
                )
            )
            blocked = True
    return GuardrailResult(
        guard_name="tool_scope_guard",
        passed=not blocked,
        blocked=blocked,
        violations=violations,
        metadata={"agent_id": agent_id, "tool_count": str(len(tool_names))},
    )


def filter_allowed_tools(
    agent_id: str,
    tool_names: list[str],
    settings: Optional[Settings] = None,
) -> tuple[list[str], GuardrailResult]:
    """Return tool names that pass scope checks; report aggregates violations."""
    allowed: list[str] = []
    violations: list[GuardrailViolation] = []
    for idx, name in enumerate(tool_names):
        result = check_tool_call(agent_id, name, call_index=idx, settings=settings)
        if result.passed:
            allowed.append(name)
        else:
            violations.extend(result.violations)
    blocked = len(allowed) == 0 and len(tool_names) > 0
    return allowed, GuardrailResult(
        guard_name="tool_scope_guard",
        passed=not blocked,
        blocked=blocked,
        violations=violations,
        metadata={"agent_id": agent_id, "allowed_count": str(len(allowed))},
    )
