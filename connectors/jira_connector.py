"""JIRA connector — JQL search (live + sim)."""

from __future__ import annotations

import json
from typing import Any

import httpx

from aaf.config import ConnectorMode
from connectors.base import BaseConnector, FetchContext


class JiraConnector(BaseConnector):
    name = "jira"

    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        if self.settings.connector_mode == ConnectorMode.SIM:
            path = self.settings.fixtures_dir / "jira" / "evidence.json"
            if not path.exists():
                return {"simulated": True, "issues": []}
            return json.loads(path.read_text(encoding="utf-8"))
        return await self._fetch_live(ctx)

    async def _fetch_live(self, ctx: FetchContext) -> dict[str, Any]:
        base = self.settings.jira_url.rstrip("/")
        email = self.settings.jira_email
        token = self.settings.jira_api_token
        if not base or not email or not token:
            return {"error": "missing JIRA_URL, JIRA_EMAIL, or JIRA_API_TOKEN", "simulated": False}
        auth = (email, token)
        projects = ctx.get("jira_projects") or []
        if not projects and ctx.get("jira_project"):
            projects = [ctx.get("jira_project")]
            
        valid_projects = [p.strip() for p in projects if p and p.strip()]
        if valid_projects:
            proj_list = ", ".join(f'"{p}"' for p in valid_projects)
            jql = f'project IN ({proj_list}) AND status != Done ORDER BY updated DESC'
        else:
            jql = "project is not EMPTY AND status != Done ORDER BY updated DESC"
        url = f"{base}/rest/api/3/search/jql"
        payload = {
            "jql": jql,
            "maxResults": 50,
            "fields": ["summary", "status", "issuetype", "priority", "labels"]
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    url,
                    auth=auth,
                    json=payload,
                )
                if r.status_code != 200:
                    return {"error": f"Jira API error ({r.status_code}): {r.text}", "status": r.status_code, "simulated": False}
                
                # Inject base URL so normalizer can construct browse links
                data = r.json()
                data["_base_url"] = base
                return data
        except Exception as exc:
            return {"error": f"Jira connection failed: {str(exc)}", "simulated": False}
