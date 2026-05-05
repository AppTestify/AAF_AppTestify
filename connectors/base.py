"""Base connector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypedDict

from aaf.config import Settings


class FetchContext(TypedDict, total=False):
    prompt: str
    github_repo: str
    jira_project: str


class BaseConnector(ABC):
    name: str

    def __init__(self, settings: Settings):
        self.settings = settings

    @abstractmethod
    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        """Return connector-specific raw payload (dict)."""
        ...
