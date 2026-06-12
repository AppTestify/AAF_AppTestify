"""GitHub commit activity and hotfix scope risk."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.github_client import github_get
from tools.sim_data import load_tools_fixture

_HIGH_RISK_PREFIXES = ("payment/", "payments/", "auth/", "billing/")


async def get_commit_activity(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    since = (now - timedelta(hours=24)).isoformat().replace("+00:00", "Z")
    branch = ctx.release_branch or "main"
    raw: dict[str, Any] = {
        "commit_count_24h": 0,
        "files_changed": 0,
        "lines_added": 0,
        "lines_deleted": 0,
        "authors_count": 0,
        "high_risk_path_touched": False,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "devops_commit_activity")
        raw.update({k: data.get(k, raw[k]) for k in raw})
    else:
        commits = await github_get(ctx, "/commits", params={"sha": branch, "since": since, "per_page": 50})
        if isinstance(commits, list):
            raw["commit_count_24h"] = len(commits)
            authors = set()
            for c in commits:
                author = (c.get("commit") or {}).get("author", {}).get("name")
                if author:
                    authors.add(author)
            raw["authors_count"] = len(authors)
            if commits:
                head = commits[0].get("sha")
                base_sha = commits[-1].get("sha") if len(commits) > 1 else head
                if head and base_sha:
                    compare = await github_get(ctx, f"/compare/{base_sha}...{head}")
                    if isinstance(compare, dict):
                        raw["files_changed"] = len(compare.get("files") or [])
                        raw["lines_added"] = int((compare.get("stats") or {}).get("additions") or 0)
                        raw["lines_deleted"] = int((compare.get("stats") or {}).get("deletions") or 0)
                        for f in compare.get("files") or []:
                            fn = str(f.get("filename") or "")
                            if any(fn.startswith(p) for p in _HIGH_RISK_PREFIXES):
                                raw["high_risk_path_touched"] = True

    risk = 0.1
    if raw["high_risk_path_touched"]:
        risk += 0.35
    if raw["files_changed"] > 15:
        risk += 0.25
    if raw["lines_added"] + raw["lines_deleted"] > 500:
        risk += 0.2
    risk = min(1.0, risk)

    lines = [
        f"Commits (24h): {raw['commit_count_24h']}, files changed: {raw['files_changed']}",
        f"Lines +{raw['lines_added']} / -{raw['lines_deleted']}",
    ]
    if raw["high_risk_path_touched"]:
        lines.append("High-risk paths (payment/auth) touched in recent commits")

    return ToolResult(
        tool_name="get_commit_activity",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
