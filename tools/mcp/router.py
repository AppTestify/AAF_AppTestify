"""Route tool execution through MCP with direct API fallback."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.mcp.client import build_tool_args, call_mcp_tool, mcp_enabled
from tools.mcp.mappings import resolve_mcp_mapping
from tools.mcp.normalizers import build_tool_result_from_mcp


async def run_with_transport(
    ctx: ToolContext,
    *,
    agileops_tool: str,
    mcp_tool: str | None,
    direct_fn: Callable[[ToolContext], Awaitable[ToolResult]],
) -> ToolResult:
    """Try MCP when configured; otherwise run direct/sim implementation."""
    if ctx.sim_mode:
        result = await direct_fn(ctx)
        result.raw_signals = {**result.raw_signals, "transport": "sim"}
        return result

    mapping = resolve_mcp_mapping(agileops_tool, mcp_tool)
    if mapping and mcp_enabled(ctx, mapping[0]):
        server_id, tool_name = mapping
        payload = await call_mcp_tool(
            ctx,
            server_id=server_id,
            tool_name=tool_name,
            arguments=build_tool_args(ctx, agileops_tool),
        )
        if payload is not None:
            mcp_result = build_tool_result_from_mcp(agileops_tool, payload, ctx)
            if mcp_result is not None:
                return mcp_result

    result = await direct_fn(ctx)
    result.raw_signals = {**result.raw_signals, "transport": "direct_api"}
    return result
