"""SAST / SonarCloud quality gate results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from agents.schemas import ToolResult
from tools.context import ToolContext, cached_tool
from tools.sim_data import load_tools_fixture


def _sast_config(ctx: ToolContext) -> dict[str, Any]:
    prefs = ctx.extra.get("ui_preferences") if isinstance(ctx.extra.get("ui_preferences"), dict) else {}
    sast = prefs.get("sast") or ctx.extra.get("sast") or {}
    return sast if isinstance(sast, dict) else {}


@cached_tool("get_sast_results")
async def get_sast_results(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    raw: dict[str, Any] = {
        "quality_gate_status": "OK",
        "security_hotspots": [],
        "coverage_pct": 0.0,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "devsecops_sast_results")
        raw.update({k: data.get(k, raw[k]) for k in raw})
    else:
        cfg = _sast_config(ctx)
        org = str(cfg.get("org") or "")
        project = str(cfg.get("project_key") or cfg.get("project") or "")
        token = str(cfg.get("api_token") or "")
        if org and project and token:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    status_resp = await client.get(
                        f"https://sonarcloud.io/api/qualitygates/project_status",
                        params={"projectKey": f"{org}_{project}"},
                        auth=(token, ""),
                    )
                    if status_resp.status_code == 200:
                        st = status_resp.json().get("projectStatus") or {}
                        raw["quality_gate_status"] = str(st.get("status") or "OK")
                    issues_resp = await client.get(
                        "https://sonarcloud.io/api/issues/search",
                        params={
                            "componentKeys": f"{org}_{project}",
                            "types": "SECURITY_HOTSPOT",
                            "ps": 10,
                        },
                        auth=(token, ""),
                    )
                    if issues_resp.status_code == 200:
                        raw["security_hotspots"] = [
                            str(i.get("message", ""))[:80]
                            for i in (issues_resp.json().get("issues") or [])[:5]
                        ]
                    meas_resp = await client.get(
                        "https://sonarcloud.io/api/measures/component",
                        params={"component": f"{org}_{project}", "metricKeys": "coverage"},
                        auth=(token, ""),
                    )
                    if meas_resp.status_code == 200:
                        measures = (meas_resp.json().get("component") or {}).get("measures") or []
                        for m in measures:
                            if m.get("metric") == "coverage":
                                raw["coverage_pct"] = float(m.get("value") or 0)
            except Exception:
                pass

    risk = 0.05
    if str(raw["quality_gate_status"]).upper() not in ("OK", "PASSED"):
        risk = 0.75
    if raw["security_hotspots"]:
        risk = min(1.0, risk + len(raw["security_hotspots"]) * 0.05)

    lines = [
        f"Quality gate: {raw['quality_gate_status']}",
        f"Coverage: {raw['coverage_pct']}%",
    ]
    if raw["security_hotspots"]:
        lines.append(f"Security hotspots: {len(raw['security_hotspots'])}")

    return ToolResult(
        tool_name="get_sast_results",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
