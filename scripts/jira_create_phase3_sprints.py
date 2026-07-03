#!/usr/bin/env python3
"""Create P1 through P6 sprints on CAS board 134 and assign Phase 3 pipeline stories."""

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
        "name": "P1 — LLM Intent Router",
        "goal": "Semantic intent router, pipeline wiring, fallback + tests.",
        "stories": ["CAS-184", "CAS-185", "CAS-186"],
        "tasks": ["T-162", "T-163", "T-164"],
        "start": datetime(2026, 8, 25, 9, 0, 0),
        "days": 4,
    },
    {
        "name": "P2 — Evidence Package",
        "goal": "Evidence package builder, package-backed tools, selective refresh.",
        "stories": ["CAS-187", "CAS-188", "CAS-189"],
        "tasks": ["T-165", "T-166", "T-167"],
        "start": datetime(2026, 9, 1, 9, 0, 0),
        "days": 5,
    },
    {
        "name": "P3 — ReAct Tool Loop",
        "goal": "Selective ReAct loop, LLM call counter, 7–9 call budget.",
        "stories": ["CAS-190", "CAS-191", "CAS-192"],
        "tasks": ["T-168", "T-169", "T-170"],
        "start": datetime(2026, 9, 8, 9, 0, 0),
        "days": 5,
    },
    {
        "name": "P4 — HOLD_RELEASE",
        "goal": "HOLD_RELEASE action, utility scoring, guards + explainer.",
        "stories": ["CAS-193", "CAS-194", "CAS-195"],
        "tasks": ["T-171", "T-172", "T-173"],
        "start": datetime(2026, 9, 15, 9, 0, 0),
        "days": 3,
    },
    {
        "name": "P5 — CAS-115 Phase 3 UI",
        "goal": "Intent router step, tool-call counts, HOLD_RELEASE styling.",
        "stories": ["CAS-196", "CAS-197", "CAS-198"],
        "tasks": ["T-174", "T-175", "T-176"],
        "start": datetime(2026, 9, 18, 9, 0, 0),
        "days": 4,
    },
    {
        "name": "P6 — MCP Validation",
        "goal": "MCP production runbook, E2E script, transport observability.",
        "stories": ["CAS-199", "CAS-200", "CAS-201"],
        "tasks": ["T-177", "T-178", "T-179"],
        "start": datetime(2026, 9, 22, 9, 0, 0),
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


def apply_keys_file(sprints: list[dict], keys_file: Path) -> list[dict]:
    data = json.loads(keys_file.read_text())
    task_to_key: dict[str, str] = {}
    if "stories" in data:
        task_to_key = data["stories"]
    elif isinstance(data, dict):
        task_to_key = {k: v for k, v in data.items() if k.startswith("T-")}

    updated: list[dict] = []
    for spec in sprints:
        spec = dict(spec)
        if task_to_key:
            spec["stories"] = [task_to_key[t] for t in spec["tasks"]]
        updated.append(spec)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sprint", type=int, help="Create only P{n} (1-6)")
    parser.add_argument(
        "--keys-file",
        type=Path,
        help="JSON file mapping task IDs to CAS keys, e.g. {\"T-162\": \"CAS-184\", ...}",
    )
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
    if args.keys_file:
        sprints = apply_keys_file(sprints, args.keys_file)
    if args.sprint:
        sprints = [sprints[args.sprint - 1]]

    for spec in sprints:
        if any(k == "CAS-XXX" for k in spec["stories"]):
            print(f"Skipping {spec['name']}: placeholder keys — pass --keys-file or update SPRINTS")
            continue
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
