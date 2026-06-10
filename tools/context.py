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
    )
