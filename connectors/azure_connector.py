"""Azure DevOps connector — repos, pipelines, work items (sim + live telemetry)."""

from __future__ import annotations

import json
from typing import Any

from aaf.config import ConnectorMode
from connectors.base import BaseConnector, FetchContext


class AzureDevOpsConnector(BaseConnector):
    name = "azure_devops"

    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        if self.settings.connector_mode == ConnectorMode.SIM:
            path = self.settings.fixtures_dir / "azure" / "evidence.json"
            if not path.exists():
                return {"simulated": True, "pipelines": [], "work_items": [], "repos": []}
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            from app.services.azure_live import fetch_azure_telemetry

            telemetry = fetch_azure_telemetry()
            return {"simulated": False, **telemetry}
        except Exception as exc:
            return {"error": str(exc), "simulated": False, "pipelines": [], "work_items": []}
