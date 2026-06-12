"""MCP transport router tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from aaf.config import ConnectorMode, Settings
from agents.schemas import ToolResult
from tools.context import build_tool_context
from tools.mcp.router import run_with_transport


@pytest.mark.asyncio
async def test_run_with_transport_sim_mode():
    settings = Settings()
    settings.connector_mode = ConnectorMode.SIM
    ctx = build_tool_context(settings)

    async def direct_fn(c):
        return ToolResult(
            tool_name="get_ci_status",
            signal=0.1,
            captured_at=datetime.now(timezone.utc),
            raw_signals={"ci_pass_rate": 1.0},
            evidence_lines=[],
        )

    result = await run_with_transport(
        ctx,
        agileops_tool="get_ci_status",
        mcp_tool="list_workflow_runs",
        direct_fn=direct_fn,
    )
    assert result.raw_signals.get("transport") == "sim"


@pytest.mark.asyncio
async def test_run_with_transport_mcp_disabled_uses_direct():
    settings = Settings()
    settings.connector_mode = ConnectorMode.LIVE
    ctx = build_tool_context(settings, extra={"ui_preferences": {"mcp_enabled": False}})

    async def direct_fn(c):
        return ToolResult(
            tool_name="get_ci_status",
            signal=0.2,
            captured_at=datetime.now(timezone.utc),
            raw_signals={"ci_pass_rate": 0.5},
            evidence_lines=["ok"],
        )

    result = await run_with_transport(
        ctx,
        agileops_tool="get_ci_status",
        mcp_tool="list_workflow_runs",
        direct_fn=direct_fn,
    )
    assert result.raw_signals.get("transport") == "direct_api"
    assert result.raw_signals["ci_pass_rate"] == 0.5


@pytest.mark.asyncio
async def test_run_with_transport_mcp_success():
    settings = Settings()
    settings.connector_mode = ConnectorMode.LIVE
    ctx = build_tool_context(
        settings,
        extra={
            "ui_preferences": {
                "mcp_enabled": True,
                "mcp_servers": {
                    "github": {"command": "npx", "args": ["-y", "pkg"], "env_ref": "github_token"},
                },
            }
        },
    )

    async def direct_fn(c):
        return ToolResult(
            tool_name="scan_cves",
            signal=0.0,
            captured_at=datetime.now(timezone.utc),
            raw_signals={"critical_count": 99},
            evidence_lines=[],
        )

    mcp_payload = {"alerts": [{"severity": "critical"}, {"severity": "high"}]}
    with patch("tools.mcp.router.call_mcp_tool", new_callable=AsyncMock) as mock_mcp:
        mock_mcp.return_value = mcp_payload
        result = await run_with_transport(
            ctx,
            agileops_tool="scan_cves",
            mcp_tool="list_code_scanning_alerts",
            direct_fn=direct_fn,
        )

    assert result.raw_signals.get("transport") == "mcp"
    assert result.raw_signals.get("critical_count") == 1


@pytest.mark.asyncio
async def test_run_with_transport_mcp_failure_falls_back():
    settings = Settings()
    settings.connector_mode = ConnectorMode.LIVE
    ctx = build_tool_context(
        settings,
        extra={
            "ui_preferences": {
                "mcp_enabled": True,
                "mcp_servers": {"github": {"command": "npx", "args": [], "env_ref": "github_token"}},
            }
        },
    )

    async def direct_fn(c):
        return ToolResult(
            tool_name="get_ci_status",
            signal=0.3,
            captured_at=datetime.now(timezone.utc),
            raw_signals={"ci_pass_rate": 0.8, "blocking_check": False, "failed_steps": [], "runs_in_window": 1},
            evidence_lines=[],
        )

    with patch("tools.mcp.router.call_mcp_tool", new_callable=AsyncMock) as mock_mcp:
        mock_mcp.return_value = None
        result = await run_with_transport(
            ctx,
            agileops_tool="get_ci_status",
            mcp_tool="list_workflow_runs",
            direct_fn=direct_fn,
        )

    assert result.raw_signals.get("transport") == "direct_api"
    assert result.raw_signals["ci_pass_rate"] == 0.8
