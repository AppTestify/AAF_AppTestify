"""Resolve AgileOps tool names to MCP server + tool."""

from __future__ import annotations

from functools import lru_cache

from agents.tool_registry import load_tool_registry

_SERVER_ALIASES = {
    "github-mcp": "github",
    "atlassian-mcp": "atlassian",
}


@lru_cache(maxsize=1)
def _registry_mcp_map() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for entry in load_tool_registry().tools:
        for mapping in entry.mcp_mappings:
            if "→" not in mapping:
                continue
            server_raw, tool_name = [p.strip() for p in mapping.split("→", 1)]
            server_id = _SERVER_ALIASES.get(server_raw, server_raw.replace("-mcp", ""))
            out[entry.function_name] = (server_id, tool_name)
    return out


def resolve_mcp_mapping(agileops_tool: str, mcp_tool: str | None = None) -> tuple[str, str] | None:
    """Return (server_id, mcp_tool_name) for an AgileOps tool."""
    mapped = _registry_mcp_map().get(agileops_tool)
    if mapped is None:
        if mcp_tool:
            return ("github", mcp_tool)
        return None
    server_id, tool_name = mapped
    if mcp_tool and mcp_tool != tool_name:
        return (server_id, mcp_tool)
    return (server_id, tool_name)
