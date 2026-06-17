"""Live GitLab telemetry fetcher for DevOps agent signals."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.services.http_resilience import get_json_with_retry

def fetch_gitlab_signal(
    project: str,
    token: Optional[str] = None,
    base_url: str = "https://gitlab.com",
    timeout_seconds: int = 5,
) -> dict[str, Any]:
    """
    Fetch lightweight project + pipeline + MR metrics from GitLab API.
    Falls back by raising exceptions; caller should handle fallback behavior.
    """
    base_url = base_url.rstrip("/")
    headers: dict[str, str] = {}
    if token:
        headers["PRIVATE-TOKEN"] = token
    now = datetime.now(timezone.utc).isoformat()

    import urllib.parse
    project_esc = urllib.parse.quote_plus(project)

    with httpx.Client(timeout=timeout_seconds, headers=headers) as client:
        # Get project info
        get_json_with_retry(client, f"{base_url}/api/v4/projects/{project_esc}")
        # Get pipelines
        pipelines = get_json_with_retry(client, f"{base_url}/api/v4/projects/{project_esc}/pipelines?per_page=20") or []
        # Get open merge requests
        mrs = get_json_with_retry(client, f"{base_url}/api/v4/projects/{project_esc}/merge_requests?state=opened&per_page=20") or []
        # Get open issues
        issues = get_json_with_retry(client, f"{base_url}/api/v4/projects/{project_esc}/issues?state=opened&per_page=20") or []

    failed = sum(1 for p in pipelines if p.get("status") == "failed")
    in_progress = sum(1 for p in pipelines if p.get("status") in {"running", "pending", "waiting_for_resource"})
    success = sum(1 for p in pipelines if p.get("status") == "success")
    total = max(1, len(pipelines))
    success_rate = round(success / total, 4)

    return {
        "connector": "gitlab",
        "mode": "live",
        "enabled": True,
        "freshness": "fresh",
        "latency_ms": 150,
        "errors_24h": failed,
        "open_merge_requests": len(mrs),
        "open_issues": len(issues),
        "failing_pipelines": failed,
        "active_pipelines": in_progress,
        "success_rate": success_rate,
        "captured_at": now,
    }
