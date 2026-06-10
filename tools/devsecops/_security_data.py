"""Load security scan data from fixtures or GitHub APIs."""

from __future__ import annotations

from typing import Any

from tools.context import ToolContext
from tools.github_client import github_get
from tools.sim_data import load_tools_fixture


async def load_security_bundle(ctx: ToolContext) -> dict[str, Any]:
    if ctx.sim_mode:
        return load_tools_fixture(ctx.fixtures_dir, "devsecops_security") or {
            "cves": {"critical": 0, "high": 0, "packages": []},
            "secrets_detected": False,
            "secret_files": [],
            "policy_violations": 0,
            "violated_rules": [],
            "dependencies": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        }

    bundle: dict[str, Any] = {
        "cves": {"critical": 0, "high": 0, "packages": []},
        "secrets_detected": False,
        "secret_files": [],
        "policy_violations": 0,
        "violated_rules": [],
        "dependencies": {"critical": 0, "high": 0, "medium": 0, "low": 0},
    }

    parts = ctx.github_repo.split("/") if "/" in ctx.github_repo else []
    if len(parts) != 2:
        return bundle
    owner, repo = parts

    alerts = await github_get(ctx, f"/repos/{owner}/{repo}/dependabot/alerts", params={"per_page": 50})
    if isinstance(alerts, list):
        for alert in alerts:
            if str(alert.get("state", "")).lower() != "open":
                continue
            sev = str((alert.get("security_advisory") or {}).get("severity", "")).lower()
            pkg = (alert.get("security_vulnerability") or {}).get("package", {})
            name = f"{pkg.get('ecosystem', '')}:{pkg.get('name', '')}"
            if sev == "critical":
                bundle["cves"]["critical"] += 1
            elif sev in {"high", "moderate"}:
                bundle["cves"]["high"] += 1
            if name and name not in bundle["cves"]["packages"]:
                bundle["cves"]["packages"].append(name)

    secrets = await github_get(ctx, f"/repos/{owner}/{repo}/secret-scanning/alerts", params={"per_page": 20})
    if isinstance(secrets, list):
        open_secrets = [s for s in secrets if str(s.get("state", "")).lower() == "open"]
        bundle["secrets_detected"] = len(open_secrets) > 0
        bundle["secret_files"] = [
            str(s.get("html_url", "")) for s in open_secrets[:5]
        ]

    return bundle
