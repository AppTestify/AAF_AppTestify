"""GitLab connector — MRs, pipelines (live + sim)."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any

import httpx

from aaf.config import ConnectorMode
from connectors.base import BaseConnector, FetchContext


class GitLabConnector(BaseConnector):
    name = "gitlab"

    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        if self.settings.connector_mode == ConnectorMode.SIM:
            path = self.settings.fixtures_dir / "gitlab" / "evidence.json"
            if not path.exists():
                return {"simulated": True, "merge_requests": [], "pipelines": []}
            return json.loads(path.read_text(encoding="utf-8"))
        return await self._fetch_live(ctx)

    async def _fetch_live(self, ctx: FetchContext) -> dict[str, Any]:
        token = getattr(self.settings, "gitlab_token", None) or ""
        project = (getattr(self.settings, "gitlab_project_id", None) or "").strip()
        base_url = (getattr(self.settings, "gitlab_url", None) or "https://gitlab.com").rstrip("/")
        if not token or not project:
            return {"error": "missing gitlab config", "simulated": False}
        project_esc = urllib.parse.quote_plus(project)
        headers = {"PRIVATE-TOKEN": token}
        out: dict[str, Any] = {"simulated": False, "project_id": project_esc}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                mrs = await client.get(
                    f"{base_url}/api/v4/projects/{project_esc}/merge_requests",
                    headers=headers,
                    params={"state": "opened", "per_page": 20},
                )
                out["merge_requests"] = mrs.json() if mrs.status_code == 200 else []
                pipes = await client.get(
                    f"{base_url}/api/v4/projects/{project_esc}/pipelines",
                    headers=headers,
                    params={"per_page": 15},
                )
                out["pipelines"] = pipes.json() if pipes.status_code == 200 else []
                issues = await client.get(
                    f"{base_url}/api/v4/projects/{project_esc}/issues",
                    headers=headers,
                    params={"state": "opened", "per_page": 20},
                )
                out["issues"] = issues.json() if issues.status_code == 200 else []
            return out
        except Exception as exc:
            return {"error": str(exc), "simulated": False}
