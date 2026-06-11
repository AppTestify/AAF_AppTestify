"""Bitbucket connector — PRs, pipelines, issues (sim + stub live)."""

from __future__ import annotations

import json
from typing import Any

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
        return {"simulated": False, "pull_requests": [], "pipelines": [], "issues": [], "note": "configure BITBUCKET_* env"}
