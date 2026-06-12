#!/usr/bin/env python3
"""Create UI-S1 through UI-S6 sprints on CAS board 134 and assign stories."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD_ID = 134

SPRINTS: list[dict] = [
    {
        "name": "UI-S1 — Design System",
        "goal": "WorkspacePageShell, buttons, SegmentedTabs, PaginationBar, CSS split.",
        "stories": ["CAS-131", "CAS-130", "CAS-132", "CAS-133", "CAS-134", "CAS-135"],
        "start": datetime(2026, 6, 16, 9, 0, 0),
        "days": 5,
    },
    {
        "name": "UI-S2 — Command Center Charts",
        "goal": "Recharts, core charts, Command Center redesign, useDashboardSummary.",
        "stories": ["CAS-136", "CAS-137", "CAS-138", "CAS-139", "CAS-140"],
        "start": datetime(2026, 6, 23, 9, 0, 0),
        "days": 5,
    },
    {
        "name": "UI-S3 — Reports Hub",
        "goal": "Tabbed Reports with chart grids and date filters.",
        "stories": ["CAS-141", "CAS-142", "CAS-143", "CAS-144", "CAS-145"],
        "start": datetime(2026, 6, 30, 9, 0, 0),
        "days": 5,
    },
    {
        "name": "UI-S4 — Pagination",
        "goal": "API totals + PaginationBar on all list pages.",
        "stories": ["CAS-146", "CAS-147", "CAS-148", "CAS-149", "CAS-150"],
        "start": datetime(2026, 7, 7, 9, 0, 0),
        "days": 4,
    },
    {
        "name": "UI-S5 — Page Polish",
        "goal": "Portfolio, Integrations, Brief, Settings split, Onboarding.",
        "stories": ["CAS-151", "CAS-152", "CAS-153", "CAS-154", "CAS-155", "CAS-156"],
        "start": datetime(2026, 7, 14, 9, 0, 0),
        "days": 5,
    },
    {
        "name": "UI-S6 — Charts & Quality",
        "goal": "Timeseries API, advanced charts, tests, design doc.",
        "stories": ["CAS-158", "CAS-157", "CAS-159", "CAS-160", "CAS-161", "CAS-162"],
        "start": datetime(2026, 7, 21, 9, 0, 0),
        "days": 4,
    },
]


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def request(method: str, url: str, auth: str, body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {"error": str(exc)}
        except json.JSONDecodeError:
            payload = {"error": raw or str(exc)}
        return exc.code, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, help="Create only UI-S{n} (1-6)")
    args = parser.parse_args()

    env = {**load_env(ROOT / ".env"), **os.environ}
    email = env.get("JIRA_EMAIL", "").strip()
    token = env.get("JIRA_API_TOKEN", "").strip()
    base_url = env.get("JIRA_URL", "https://apptestify.atlassian.net").rstrip("/")
    if not email or not token:
        print("Set JIRA_EMAIL and JIRA_API_TOKEN in .env")
        return 1

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    sprints = SPRINTS
    if args.sprint:
        sprints = [SPRINTS[args.sprint - 1]]

    for spec in sprints:
        end = spec["start"] + timedelta(days=spec["days"])
        status, sprint = request(
            "POST",
            f"{base_url}/rest/agile/1.0/sprint",
            auth,
            {
                "name": spec["name"],
                "originBoardId": BOARD_ID,
                "goal": spec["goal"],
                "startDate": spec["start"].strftime("%Y-%m-%dT%H:%M:%S.000+0530"),
                "endDate": end.strftime("%Y-%m-%dT%H:%M:%S.000+0530"),
            },
        )
        if status not in (200, 201):
            print(f"Failed {spec['name']}: {json.dumps(sprint, indent=2)}")
            return 1
        sprint_id = sprint["id"]
        assign_status, assign_resp = request(
            "POST",
            f"{base_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
            auth,
            {"issues": spec["stories"]},
        )
        if assign_status not in (200, 204):
            print(f"Assign failed {spec['name']}: {json.dumps(assign_resp, indent=2)}")
            return 1
        print(f"Created sprint {sprint_id} ({spec['name']}), assigned {len(spec['stories'])} stories")

    return 0


if __name__ == "__main__":
    sys.exit(main())
