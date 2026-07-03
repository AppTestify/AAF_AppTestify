#!/usr/bin/env python3
"""Create R1 through R4 sprints on CAS board 134 and assign reports/notification stories."""

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
        "name": "R1 — Report Exports",
        "goal": "Report catalog, XLSX/PDF engines, API endpoints, Exports tab buttons.",
        "stories": ["CAS-164", "CAS-165", "CAS-166", "CAS-167", "CAS-168"],
        "tasks": ["T-143", "T-144", "T-145", "T-146", "T-147"],
        "start": datetime(2026, 7, 28, 9, 0, 0),
        "days": 5,
    },
    {
        "name": "R2 — Platform SMTP",
        "goal": "PlatformNotificationConfig, SMTP resolver, template catalog, superadmin UI.",
        "stories": ["CAS-169", "CAS-171", "CAS-170", "CAS-172", "CAS-173"],
        "tasks": ["T-148", "T-149", "T-150", "T-151", "T-152"],
        "start": datetime(2026, 8, 4, 9, 0, 0),
        "days": 5,
    },
    {
        "name": "R3 — Slack & Teams",
        "goal": "Teams webhook, enhanced Slack, notification router, tenant toggles.",
        "stories": ["CAS-174", "CAS-175", "CAS-176", "CAS-177"],
        "tasks": ["T-153", "T-154", "T-155", "T-156"],
        "start": datetime(2026, 8, 11, 9, 0, 0),
        "days": 4,
    },
    {
        "name": "R4 — Email Reports",
        "goal": "On-demand email reports, digest schedule, Celery beat, tests + docs.",
        "stories": ["CAS-178", "CAS-179", "CAS-180", "CAS-181", "CAS-182"],
        "tasks": ["T-157", "T-158", "T-159", "T-160", "T-161"],
        "start": datetime(2026, 8, 18, 9, 0, 0),
        "days": 5,
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
    parser.add_argument("--sprint", type=int, help="Create only R{n} (1-4)")
    parser.add_argument(
        "--keys-file",
        type=Path,
        help="JSON file mapping task IDs to CAS keys, e.g. {\"T-143\": \"CAS-165\", ...}",
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
