#!/usr/bin/env python3
"""Validate MCP connector configuration for production tenants."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aaf.config import ConnectorMode, Settings
from tools.context import build_tool_context
from tools.mcp.client import _resolve_env, _server_config, mcp_enabled
from tools.mcp.mappings import resolve_mcp_mapping


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _ui_preferences_from_env(env: dict[str, str]) -> dict[str, Any]:
    raw = env.get("MCP_UI_PREFERENCES_JSON", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    enabled = env.get("MCP_ENABLED", "true").lower() in ("1", "true", "yes")
    return {
        "mcp_enabled": enabled,
        "mcp_servers": {
            "github": {
                "transport": "stdio",
                "command": env.get("MCP_GITHUB_COMMAND", "npx"),
                "args": json.loads(env.get("MCP_GITHUB_ARGS", '["-y", "@modelcontextprotocol/server-github"]')),
                "env_ref": "github_token",
            },
            "atlassian": {
                "transport": "stdio",
                "command": env.get("MCP_ATLASSIAN_COMMAND", "npx"),
                "args": json.loads(
                    env.get("MCP_ATLASSIAN_ARGS", '["-y", "@modelcontextprotocol/server-atlassian"]')
                ),
                "env_ref": "jira_credentials",
            },
        },
    }


def _credential_check(server_id: str, cfg: dict[str, Any], ctx_env: dict[str, str]) -> str | None:
    env_ref = str(cfg.get("env_ref") or "")
    if server_id == "github":
        if not ctx_env.get("GITHUB_PERSONAL_ACCESS_TOKEN") and not os.environ.get("GITHUB_TOKEN"):
            return "Missing GITHUB_TOKEN / github connector token for github MCP server"
    elif server_id == "atlassian":
        if not ctx_env.get("JIRA_API_TOKEN") and not os.environ.get("JIRA_API_TOKEN"):
            return "Missing JIRA_API_TOKEN for atlassian MCP server"
    elif env_ref and env_ref not in ("github_token", "jira_credentials"):
        return f"Unknown env_ref '{env_ref}' — verify credential mapping"
    return None


async def _probe_server(server_id: str, ctx, timeout_s: float) -> dict[str, Any]:
    cfg = _server_config(ctx, server_id)
    if not cfg:
        return {"server_id": server_id, "ok": False, "error": "Server not configured in ui_preferences"}

    command = str(cfg.get("command") or "").strip()
    if not command:
        return {"server_id": server_id, "ok": False, "error": "Missing command in mcp_servers config"}

    env = _resolve_env(ctx, str(cfg.get("env_ref") or ""))
    cred_err = _credential_check(server_id, cfg, env)
    if cred_err:
        return {"server_id": server_id, "ok": False, "error": cred_err}

    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        return {
            "server_id": server_id,
            "ok": False,
            "error": "Python 'mcp' package not installed — pip install mcp",
        }

    args_list = [str(a) for a in (cfg.get("args") or [])]
    params = StdioServerParameters(command=command, args=args_list, env=env)

    async def _run() -> dict[str, Any]:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = [t.name for t in (tools.tools or [])]
                return {"tool_count": len(names), "sample_tools": names[:5]}

    try:
        payload = await asyncio.wait_for(_run(), timeout=timeout_s)
        return {"server_id": server_id, "ok": True, **payload}
    except asyncio.TimeoutError:
        return {"server_id": server_id, "ok": False, "error": f"Initialize timed out after {timeout_s}s"}
    except Exception as exc:  # noqa: BLE001
        return {"server_id": server_id, "ok": False, "error": str(exc)}


def _registry_mcp_coverage(ctx) -> list[dict[str, Any]]:
    samples = [
        "get_ci_status",
        "get_pr_status",
        "count_blockers",
        "get_open_defects",
        "scan_cves",
    ]
    rows: list[dict[str, Any]] = []
    for tool in samples:
        mapping = resolve_mcp_mapping(tool)
        if not mapping:
            rows.append({"tool": tool, "mapped": False})
            continue
        server_id, mcp_tool = mapping
        rows.append(
            {
                "tool": tool,
                "mapped": True,
                "server_id": server_id,
                "mcp_tool": mcp_tool,
                "server_enabled": mcp_enabled(ctx, server_id),
            }
        )
    return rows


async def run_validation(*, server_filter: str | None, timeout_s: float) -> dict[str, Any]:
    env = {**load_env(ROOT / ".env"), **os.environ}
    prefs = _ui_preferences_from_env(env)
    settings = Settings()
    settings.connector_mode = ConnectorMode.LIVE
    settings.github_token = env.get("GITHUB_TOKEN", "")
    settings.jira_api_token = env.get("JIRA_API_TOKEN", "")
    settings.jira_email = env.get("JIRA_EMAIL", "")
    settings.jira_url = env.get("JIRA_URL", "")
    ctx = build_tool_context(settings, extra={"ui_preferences": prefs})

    if not prefs.get("mcp_enabled"):
        return {"ok": False, "error": "mcp_enabled is false in UI preferences", "servers": [], "registry": []}

    servers_cfg = prefs.get("mcp_servers") or {}
    server_ids = sorted(servers_cfg.keys())
    if server_filter:
        server_ids = [s for s in server_ids if s == server_filter]
        if not server_ids:
            return {"ok": False, "error": f"Server '{server_filter}' not in mcp_servers", "servers": [], "registry": []}

    results = [await _probe_server(sid, ctx, timeout_s) for sid in server_ids]
    registry = _registry_mcp_coverage(ctx)
    ok = all(r.get("ok") for r in results) and all(r.get("server_enabled", True) for r in registry if r.get("mapped"))
    return {"ok": ok, "mcp_enabled": True, "servers": results, "registry": registry}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MCP connector configuration")
    parser.add_argument("--server", help="Validate only this server id (github, atlassian, …)")
    parser.add_argument("--timeout", type=float, default=30.0, help="Per-server initialize timeout (seconds)")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args()

    report = asyncio.run(run_validation(server_filter=args.server, timeout_s=args.timeout))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"MCP validation: {'PASS' if report.get('ok') else 'FAIL'}")
        if report.get("error"):
            print(f"  error: {report['error']}")
        for row in report.get("servers", []):
            status = "OK" if row.get("ok") else "FAIL"
            detail = row.get("tool_count", row.get("error", ""))
            print(f"  [{status}] {row.get('server_id')}: {detail}")
        unmapped = [r for r in report.get("registry", []) if r.get("mapped") and not r.get("server_enabled")]
        for row in unmapped:
            print(f"  [WARN] registry tool {row['tool']} maps to disabled server {row['server_id']}")

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
