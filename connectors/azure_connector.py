"""Azure DevOps connector — repos, pipelines, work items (sim + live)."""

from __future__ import annotations

import json
from typing import Any
import httpx

from aaf.config import ConnectorMode
from connectors.base import BaseConnector, FetchContext


class AzureDevOpsConnector(BaseConnector):
    name = "azure_devops"

    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        if self.settings.connector_mode == ConnectorMode.SIM:
            path = self.settings.fixtures_dir / "azure" / "evidence.json"
            if not path.exists():
                return {"simulated": True, "pipelines": [], "work_items": [], "pull_requests": []}
            return json.loads(path.read_text(encoding="utf-8"))
        return await self._fetch_live(ctx)

    async def _fetch_live(self, ctx: FetchContext) -> dict[str, Any]:
        org = self.settings.azure_organization
        project = self.settings.azure_project
        repo = self.settings.azure_repo
        pat = self.settings.azure_pat

        if not org or not project or not pat:
            return {"error": "missing AZURE_ORGANIZATION, AZURE_PROJECT, or AZURE_PAT", "simulated": False}

        auth = ("", pat)
        headers = {"Accept": "application/json"}
        base_url = f"https://dev.azure.com/{org}/{project}"
        
        out: dict[str, Any] = {"organization": org, "project": project, "repo": repo, "simulated": False}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Fetch Pipelines (Builds)
                builds_resp = await client.get(
                    f"{base_url}/_apis/build/builds",
                    auth=auth,
                    headers=headers,
                    params={"api-version": "7.1", "$top": "20"},
                )
                out["pipelines"] = builds_resp.json().get("value", []) if builds_resp.status_code == 200 else []

                # Fetch Work Items via WIQL
                wiql_query = {
                    "query": "Select [System.Id], [System.Title], [System.State] From WorkItems Where [System.State] <> 'Closed' And [System.State] <> 'Done' Order By [System.ChangedDate] Desc"
                }
                wiql_resp = await client.post(
                    f"{base_url}/_apis/wit/wiql",
                    auth=auth,
                    headers=headers,
                    json=wiql_query,
                    params={"api-version": "7.1", "$top": "20"},
                )
                
                work_items = []
                if wiql_resp.status_code == 200:
                    wiql_data = wiql_resp.json()
                    item_ids = [str(w["id"]) for w in wiql_data.get("workItems", [])[:20]]
                    if item_ids:
                        ids_str = ",".join(item_ids)
                        items_resp = await client.get(
                            f"{base_url}/_apis/wit/workitems",
                            auth=auth,
                            headers=headers,
                            params={"api-version": "7.1", "ids": ids_str},
                        )
                        if items_resp.status_code == 200:
                            work_items = items_resp.json().get("value", [])
                out["work_items"] = work_items

                # Fetch Pull Requests if repo is provided
                if repo:
                    prs_resp = await client.get(
                        f"{base_url}/_apis/git/repositories/{repo}/pullrequests",
                        auth=auth,
                        headers=headers,
                        params={"api-version": "7.1", "searchCriteria.status": "active", "$top": "20"},
                    )
                    out["pull_requests"] = prs_resp.json().get("value", []) if prs_resp.status_code == 200 else []
                else:
                    out["pull_requests"] = []

            return out
        except Exception as exc:
            return {"error": f"Azure DevOps connection failed: {str(exc)}", "simulated": False}
