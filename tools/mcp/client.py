"""MCP stdio client — calls external github-mcp / atlassian-mcp servers."""

from __future__ import annotations

import json
import os
from typing import Any

from tools.context import ToolContext


def mcp_enabled(ctx: ToolContext, server_id: str) -> bool:
    if ctx.sim_mode:
        return False
    prefs = ctx.extra.get("ui_preferences") if isinstance(ctx.extra.get("ui_preferences"), dict) else {}
    if not prefs.get("mcp_enabled"):
        return False
    servers = prefs.get("mcp_servers") or {}
    return isinstance(servers, dict) and server_id in servers


def _server_config(ctx: ToolContext, server_id: str) -> dict[str, Any] | None:
    prefs = ctx.extra.get("ui_preferences") if isinstance(ctx.extra.get("ui_preferences"), dict) else {}
    servers = prefs.get("mcp_servers") or {}
    cfg = servers.get(server_id) if isinstance(servers, dict) else None
    return cfg if isinstance(cfg, dict) else None


def _resolve_env(ctx: ToolContext, env_ref: str | None) -> dict[str, str]:
    env = dict(os.environ)
    if env_ref == "github_token" and ctx.github_token:
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = ctx.github_token
    elif env_ref == "jira_credentials":
        if ctx.jira_api_token:
            env["JIRA_API_TOKEN"] = ctx.jira_api_token
        if ctx.jira_email:
            env["JIRA_EMAIL"] = ctx.jira_email
        if ctx.jira_url:
            env["JIRA_URL"] = ctx.jira_url
    return env


def build_tool_args(ctx: ToolContext, agileops_tool: str) -> dict[str, Any]:
    """Build MCP tool arguments from ToolContext."""
    owner, name = (ctx.github_repo.split("/", 1) + [""])[:2] if "/" in ctx.github_repo else ("", "")
    args: dict[str, Any] = {
        "owner": owner,
        "repo": name,
        "repository": ctx.github_repo,
        "branch": ctx.release_branch or "main",
        "base": ctx.release_branch or "main",
        "project_key": ctx.jira_project,
        "board_id": ctx.jira_board_id,
        "state": "open",
        "per_page": 30,
    }
    if agileops_tool == "count_blockers":
        args["jql"] = f'project = {ctx.jira_project} AND sprint in openSprints() AND status = Blocked'
    elif agileops_tool == "get_open_defects":
        args["jql"] = (
            f'project = {ctx.jira_project} AND sprint in openSprints() '
            f'AND issuetype = Bug AND priority in (High, Critical) AND status != Done'
        )
    return args


async def call_mcp_tool(
    ctx: ToolContext,
    *,
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Invoke an MCP tool; returns parsed JSON payload or None on failure."""
    cfg = _server_config(ctx, server_id)
    if not cfg:
        return None
    command = str(cfg.get("command") or "")
    if not command:
        return None
    args_list = [str(a) for a in (cfg.get("args") or [])]
    env = _resolve_env(ctx, str(cfg.get("env_ref") or ""))

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        return None

    params = StdioServerParameters(command=command, args=args_list, env=env)
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments or {})
                if result.isError:
                    return None
                content = result.content or []
                for block in content:
                    text = getattr(block, "text", None)
                    if text:
                        try:
                            return json.loads(text)
                        except json.JSONDecodeError:
                            return {"text": text}
                return {"content": [getattr(c, "text", str(c)) for c in content]}
    except Exception:
        return None
