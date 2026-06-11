"""PagerDuty/Opsgenie connector — incidents for PM + DORA MTTR."""

from __future__ import annotations

import json
from typing import Any

import httpx

from aaf.config import ConnectorMode
from connectors.base import BaseConnector, FetchContext


class PagerDutyConnector(BaseConnector):
    name = "pagerduty"

    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        if self.settings.connector_mode == ConnectorMode.SIM:
            path = self.settings.fixtures_dir / "pagerduty" / "evidence.json"
            if not path.exists():
                return {"simulated": True, "incidents": []}
            return json.loads(path.read_text(encoding="utf-8"))
        token = getattr(self.settings, "pagerduty_api_token", None) or ""
        if not token:
            return {"error": "missing pagerduty token", "simulated": False}
        headers = {"Authorization": f"Token token={token}", "Accept": "application/vnd.pagerduty+json;version=2"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.pagerduty.com/incidents",
                    headers=headers,
                    params={"statuses[]": ["triggered", "acknowledged"], "limit": 25},
                )
                data = resp.json() if resp.status_code == 200 else {"incidents": []}
                return {"simulated": False, **data}
        except Exception as exc:
            return {"error": str(exc), "simulated": False}
