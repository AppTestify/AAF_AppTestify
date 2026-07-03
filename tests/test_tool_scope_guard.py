from __future__ import annotations

from aaf.config import Settings
from guardrails.tool_scope_guard import append_tool_scope_event, check_tool_call, validate_agent_tool_plan


def test_allows_devops_tools():
    result = check_tool_call("devops", "get_ci_status", settings=Settings())
    assert result.passed


def test_blocks_unknown_tool():
    result = check_tool_call("devops", "delete_repository", settings=Settings())
    assert result.blocked
    assert any(v.rule == "write_tool_blocked" for v in result.violations)


def test_validates_full_agent_plan():
    result = validate_agent_tool_plan(
        "finops",
        ["get_spend_trend", "check_budget_pace", "get_ri_coverage"],
        Settings(),
    )
    assert result.passed


def test_append_tool_scope_event():
    raw = append_tool_scope_event({}, tool_name="bad_tool", message="blocked")
    assert raw["guardrail_events"][0]["guard"] == "tool_scope_guard"
