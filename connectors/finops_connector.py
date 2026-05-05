"""FinOps — file-based cost export (live) or fixtures (sim)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from aaf.config import ConnectorMode
from connectors.base import BaseConnector, FetchContext


class FinopsConnector(BaseConnector):
    name = "finops"

    async def fetch_evidence(self, ctx: FetchContext) -> dict[str, Any]:
        if self.settings.connector_mode == ConnectorMode.SIM:
            path = self.settings.fixtures_dir / "finops" / "evidence.json"
            if not path.exists():
                return {"simulated": True, "daily_spend": [], "anomalies": []}
            return json.loads(path.read_text(encoding="utf-8"))
        return self._load_file()

    def _load_file(self) -> dict[str, Any]:
        p = self.settings.finops_cost_file
        if p is None or not Path(p).exists():
            return {
                "error": "set FINOPS_COST_FILE to a JSON or CSV path for live FinOps",
                "simulated": False,
            }
        path = Path(p)
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        if path.suffix.lower() == ".csv":
            rows: list[dict[str, str]] = []
            with path.open(newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    rows.append(dict(row))
            return {"source": "csv", "rows": rows, "simulated": False}
        return {"error": "unsupported file type", "path": str(path)}
