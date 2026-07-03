"""Contract tests: registry return fields match sim-mode ToolResult.raw_signals."""

from __future__ import annotations

import pytest

from aaf.config import ConnectorMode
from agents import devops, devsecops, finops, pm_agent
from agents.tool_registry import entry_returns_map, load_tool_registry
from tools.context import build_tool_context


_AGENT_INSTANCES = {
    "devops": devops._agent,
    "project_management": pm_agent._agent,
    "finops": finops._agent,
    "devsecops": devsecops._agent,
}


@pytest.mark.asyncio
async def test_registry_has_31_tools():
    doc = load_tool_registry()
    assert len(doc.tools) == 31


@pytest.mark.asyncio
async def test_shipped_tools_raw_signals_match_registry(settings):
    settings.connector_mode = ConnectorMode.SIM
    ctx = build_tool_context(settings)
    returns_map = entry_returns_map()

    for agent_id, agent in _AGENT_INSTANCES.items():
        for fn in agent.tool_callables():
            name = fn.__name__
            expected = returns_map.get(name)
            assert expected is not None, f"{name} missing from registry returns map"
            result = await fn(ctx)
            for key in expected:
                assert key in result.raw_signals, f"{name}: missing raw_signals key {key}"
