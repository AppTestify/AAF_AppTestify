#!/usr/bin/env python3
"""Create or complete Sprint 2 on CAS board 134."""

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
S2_STORIES = [
    "CAS-18",
    "CAS-19",
    "CAS-20",
    "CAS-21",
    "CAS-22",
    "CAS-23",
    "CAS-24",
    "CAS-25",
    "CAS-26",
]
BOARD_ID = 134
SPRINT_NAME = "S2 — Infra, CI & Queue"


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


def find_active_sprint(base_url: str, auth: str) -> dict | None:
    status, payload = request("GET", f"{base_url}/rest/agile/1.0/board/{BOARD_ID}/sprint?state=active", auth)
    if status != 200:
        return None
    for sprint in payload.get("values") or []:
        if sprint.get("name") == SPRINT_NAME:
            return sprint
    values = payload.get("values") or []
    return values[0] if values else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--complete", action="store_true", help="Close active S2 sprint")
    args = parser.parse_args()

    env = {**load_env(ROOT / ".env"), **os.environ}
    email = env.get("JIRA_EMAIL", "").strip()
    token = env.get("JIRA_API_TOKEN", "").strip()
    base_url = env.get("JIRA_URL", "https://apptestify.atlassian.net").rstrip("/")
    if not email or not token:
        print("Set JIRA_EMAIL and JIRA_API_TOKEN in .env")
        return 1

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    if args.complete:
        sprint = find_active_sprint(base_url, auth)
        if not sprint:
            print(f"No active sprint on board {BOARD_ID}")
            return 1
        status, resp = request(
            "PUT",
            f"{base_url}/rest/agile/1.0/sprint/{sprint['id']}",
            auth,
            {"state": "closed"},
        )
        if status not in (200, 204):
            print(json.dumps(resp, indent=2))
            return 1
        print(f"Closed sprint {sprint['id']}")
        return 0

    start = datetime(2026, 7, 7, 9, 0, 0)
    end = start + timedelta(days=21)
    status, sprint = request(
        "POST",
        f"{base_url}/rest/agile/1.0/sprint",
        auth,
        {
            "name": SPRINT_NAME,
            "originBoardId": BOARD_ID,
            "goal": "Celery queue, nginx, CI gates, smoke in CD.",
            "startDate": start.strftime("%Y-%m-%dT%H:%M:%S.000+0530"),
            "endDate": end.strftime("%Y-%m-%dT%H:%M:%S.000+0530"),
        },
    )
    if status not in (200, 201):
        print(json.dumps(sprint, indent=2))
        return 1
    sprint_id = sprint["id"]
    assign_status, assign_resp = request(
        "POST",
        f"{base_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
        auth,
        {"issues": S2_STORIES},
    )
    if assign_status not in (200, 204):
        print(json.dumps(assign_resp, indent=2))
        return 1
    print(f"Created sprint {sprint_id}, assigned {', '.join(S2_STORIES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
