"""GitHub connector — PRs, workflows, commits (live + sim)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from aaf.config import ConnectorMode
from connectors.base import BaseConnector, FetchContext


class GitHubConnector(BaseConnector):
    name = "github"

    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        if self.settings.connector_mode == ConnectorMode.SIM:
            path = self.settings.fixtures_dir / "github" / "evidence.json"
            if not path.exists():
                return {"simulated": True, "pull_requests": [], "workflow_runs": [], "issues": []}
            return json.loads(path.read_text(encoding="utf-8"))
        return await self._fetch_live()

    async def _fetch_live(self) -> dict[str, Any]:
        token = self.settings.github_token
        repo = self.settings.github_repo
        if not token or not repo or "/" not in repo:
            return {"error": "missing GITHUB_TOKEN or GITHUB_REPO", "simulated": False}
        owner, name = repo.split("/", 1)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        base = "https://api.github.com"
        out: dict[str, Any] = {"owner": owner, "repo": name, "simulated": False}
        async with httpx.AsyncClient(timeout=30.0) as client:
            prs = await client.get(
                f"{base}/repos/{owner}/{name}/pulls",
                headers=headers,
                params={"state": "open", "per_page": 20},
            )
            out["pull_requests"] = prs.json() if prs.status_code == 200 else []
            wf = await client.get(
                f"{base}/repos/{owner}/{name}/actions/runs",
                headers=headers,
                params={"per_page": 15},
            )
            out["workflow_runs"] = (wf.json().get("workflow_runs") or []) if wf.status_code == 200 else []
            issues = await client.get(
                f"{base}/repos/{owner}/{name}/issues",
                headers=headers,
                params={"state": "open", "per_page": 20},
            )
            out["issues"] = issues.json() if issues.status_code == 200 else []
        return out
