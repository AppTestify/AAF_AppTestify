"""Shared context passed to all agent tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aaf.config import ConnectorMode, Settings


@dataclass
class ToolContext:
    settings: Settings
    github_repo: str = ""
    github_token: str = ""
    jira_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project: str = "PROJ"
    jira_board_id: str = "1"
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    release_branch: str = "main"
    extra: dict[str, Any] = field(default_factory=dict)
    evidence_package: dict[str, Any] | None = None

    @property
    def connector_mode(self) -> ConnectorMode:
        return self.settings.connector_mode

    @property
    def fixtures_dir(self) -> Path:
        return self.settings.fixtures_dir

    @property
    def finops_cost_file(self) -> Path | None:
        return self.settings.finops_cost_file

    @property
    def sim_mode(self) -> bool:
        return self.connector_mode == ConnectorMode.SIM


def build_tool_context(
    settings: Settings,
    *,
    github_repo: str | None = None,
    jira_project: str | None = None,
    jira_board_id: str | None = None,
    release_branch: str | None = None,
    extra: dict[str, Any] | None = None,
    evidence_package: dict[str, Any] | None = None,
) -> ToolContext:
    return ToolContext(
        settings=settings,
        github_repo=github_repo or settings.github_repo,
        github_token=settings.github_token,
        jira_url=settings.jira_url,
        jira_email=settings.jira_email,
        jira_api_token=settings.jira_api_token,
        jira_project=jira_project or getattr(settings, "jira_project", "PROJ"),
        jira_board_id=jira_board_id or getattr(settings, "jira_board_id", "1"),
        aws_region=getattr(settings, "aws_region", "us-east-1"),
        aws_access_key_id=getattr(settings, "aws_access_key_id", ""),
        aws_secret_access_key=getattr(settings, "aws_secret_access_key", ""),
        release_branch=release_branch or "main",
        extra=extra or {},
        evidence_package=evidence_package,
    )


def get_cached_tool_result(ctx: ToolContext, tool_name: str):
    """Return a cached ToolResult from the evidence package, if present."""
    from agents.schemas import ToolResult

    pkg = ctx.evidence_package or {}
    tools = pkg.get("tools") or {}
    entry = tools.get(tool_name)
    if entry is None:
        return None
    if isinstance(entry, ToolResult):
        return entry
    if isinstance(entry, dict):
        return ToolResult.model_validate(entry)
    return None


def cache_tool_result(ctx: ToolContext, result) -> None:
    """Store a tool result in the evidence package cache."""
    if ctx.evidence_package is None:
        ctx.evidence_package = {}
    tools = ctx.evidence_package.setdefault("tools", {})
    tools[result.tool_name] = result.model_dump(mode="json")


def read_package_signal(ctx: ToolContext, tool_name: str, key: str, default=None):
    """Read a raw signal value from a package-backed tool result."""
    cached = get_cached_tool_result(ctx, tool_name)
    if cached is None:
        return default
    return cached.raw_signals.get(key, default)
