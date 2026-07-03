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
        return await self._fetch_live(ctx)

    async def _fetch_live(self, ctx: FetchContext) -> dict[str, Any]:
        token = self.settings.github_token
        repos = ctx.get("github_repos") or []
        if not repos and self.settings.github_repo:
            repos = [self.settings.github_repo]
            
        if not token or not repos:
            return {"error": "missing GITHUB_TOKEN or repos", "simulated": False}
            
        import asyncio
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        base = "https://api.github.com"
        
        async def fetch_repo(client: httpx.AsyncClient, repo: str) -> dict[str, Any]:
            if "/" not in repo:
                return {}
            owner, name = repo.split("/", 1)
            out = {"owner": owner, "repo": name, "pull_requests": [], "workflow_runs": [], "issues": []}
            try:
                prs = await client.get(f"{base}/repos/{owner}/{name}/pulls", headers=headers, params={"state": "open", "per_page": 20})
                out["pull_requests"] = prs.json() if prs.status_code == 200 else []
                wf = await client.get(f"{base}/repos/{owner}/{name}/actions/runs", headers=headers, params={"per_page": 15})
                out["workflow_runs"] = (wf.json().get("workflow_runs") or []) if wf.status_code == 200 else []
                issues = await client.get(f"{base}/repos/{owner}/{name}/issues", headers=headers, params={"state": "open", "per_page": 20})
                out["issues"] = issues.json() if issues.status_code == 200 else []
            except Exception:
                pass
            return out

        out = {"simulated": False, "pull_requests": [], "workflow_runs": [], "issues": []}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                tasks = [fetch_repo(client, repo) for repo in repos]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, dict) and "error" not in res:
                        repo_name = res.get("repo", "")
                        for pr in res.get("pull_requests", []):
                            pr["_repo_name"] = repo_name
                            out["pull_requests"].append(pr)
                        for wf in res.get("workflow_runs", []):
                            wf["_repo_name"] = repo_name
                            out["workflow_runs"].append(wf)
                        for issue in res.get("issues", []):
                            issue["_repo_name"] = repo_name
                            out["issues"].append(issue)
            return out
        except Exception as exc:
            return {"error": f"GitHub connection failed: {str(exc)}", "simulated": False}
