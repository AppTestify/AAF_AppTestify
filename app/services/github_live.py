"""Live GitHub telemetry fetcher for DevOps agent signals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx


def fetch_github_signal(repo: str, token: Optional[str] = None, timeout_seconds: int = 5) -> dict[str, Any]:
    """
    Fetch lightweight repo + workflow metrics from GitHub API.
    Falls back by raising exceptions; caller should handle fallback behavior.
    """
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    now = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=timeout_seconds, headers=headers) as client:
        repo_resp = client.get(f"https://api.github.com/repos/{repo}")
        repo_resp.raise_for_status()
        repo_data = repo_resp.json()

        runs_resp = client.get(f"https://api.github.com/repos/{repo}/actions/runs?per_page=20")
        runs_resp.raise_for_status()
        runs = (runs_resp.json() or {}).get("workflow_runs", []) or []

    failed = sum(1 for r in runs if r.get("conclusion") == "failure")
    in_progress = sum(1 for r in runs if r.get("status") in {"queued", "in_progress", "waiting"})
    success = sum(1 for r in runs if r.get("conclusion") == "success")
    total = max(1, len(runs))
    success_rate = round(success / total, 4)

    return {
        "connector": "github",
        "mode": "live",
        "enabled": True,
        "freshness": "fresh",
        "latency_ms": 150,
        "errors_24h": failed,
        "open_issues": int(repo_data.get("open_issues_count") or 0),
        "default_branch": repo_data.get("default_branch"),
        "failing_checks": failed,
        "active_runs": in_progress,
        "success_rate": success_rate,
        "captured_at": now,
    }
