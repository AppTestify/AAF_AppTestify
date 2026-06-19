"""Bitbucket connector — PRs, pipelines, issues (live + sim)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from aaf.config import ConnectorMode
from connectors.base import BaseConnector, FetchContext


class BitbucketConnector(BaseConnector):
    name = "bitbucket"

    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        if self.settings.connector_mode == ConnectorMode.SIM:
            path = self.settings.fixtures_dir / "bitbucket" / "evidence.json"
            if not path.exists():
                return {"simulated": True, "pull_requests": [], "pipelines": [], "issues": []}
            return json.loads(path.read_text(encoding="utf-8"))
        return await self._fetch_live()

    async def _fetch_live(self) -> dict[str, Any]:
        username = self.settings.bitbucket_username
        password = self.settings.bitbucket_app_password
        workspace = self.settings.bitbucket_workspace
        repo_slug = self.settings.bitbucket_repo_slug

        if not username or not password or not workspace or not repo_slug:
            return {"error": "missing BITBUCKET_* env configurations", "simulated": False}

        base = f"https://api.bitbucket.org/2.0/repositories/{workspace}/{repo_slug}"
        out: dict[str, Any] = {"workspace": workspace, "repo": repo_slug, "simulated": False}
        auth = (username, password)
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                prs = await client.get(
                    f"{base}/pullrequests",
                    auth=auth,
                    params={"state": "OPEN", "pagelen": 20},
                )
                out["pull_requests"] = (prs.json().get("values") or []) if prs.status_code == 200 else []
                
                pipelines = await client.get(
                    f"{base}/pipelines/",
                    auth=auth,
                    params={"sort": "-created_on", "pagelen": 15},
                )
                out["pipelines"] = (pipelines.json().get("values") or []) if pipelines.status_code == 200 else []
                
                issues = await client.get(
                    f"{base}/issues",
                    auth=auth,
                    params={"q": 'state="new" OR state="open"', "pagelen": 20},
                )
                out["issues"] = (issues.json().get("values") or []) if issues.status_code == 200 else []
            return out
        except Exception as exc:
            return {"error": f"Bitbucket connection failed: {str(exc)}", "simulated": False}
