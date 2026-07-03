#!/usr/bin/env python3
"""Create or complete Sprint 1 on CAS board 134 and assign S1 stories."""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S1_STORIES = [
    "CAS-10",
    "CAS-11",
    "CAS-12",
    "CAS-13",
    "CAS-14",
    "CAS-15",
    "CAS-16",
    "CAS-17",
]
BOARD_ID = 134
SPRINT_NAME = "S1 — Security & Infra Core"


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
    values = payload.get("values") or []
    for sprint in values:
        if sprint.get("name") == SPRINT_NAME:
            return sprint
    return values[0] if values else None


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Create or complete Sprint 1 on CAS board 134")
    parser.add_argument(
        "--complete",
        action="store_true",
        help="Close the active S1 sprint (all stories should be Done first)",
    )
    args = parser.parse_args()

    env = {**load_env(ROOT / ".env"), **os.environ}
    email = env.get("JIRA_EMAIL", "").strip()
    token = env.get("JIRA_API_TOKEN", "").strip()
    base_url = env.get("JIRA_URL", "https://apptestify.atlassian.net").rstrip("/")

    if not email or not token:
        print("Set JIRA_EMAIL and JIRA_API_TOKEN in .env (API token: id.atlassian.com → Security → API tokens)")
        return 1

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()

    if args.complete:
        sprint = find_active_sprint(base_url, auth)
        if not sprint:
            print(f"No active sprint found on board {BOARD_ID}")
            return 1
        sprint_id = sprint["id"]
        close_status, close_resp = request(
            "PUT",
            f"{base_url}/rest/agile/1.0/sprint/{sprint_id}",
            auth,
            {"state": "closed"},
        )
        if close_status not in (200, 204):
            print("Failed to close sprint:", json.dumps(close_resp, indent=2))
            return 1
        print(f"Closed sprint {sprint_id}: {sprint.get('name')}")
        print(f"Board: {base_url}/jira/software/projects/CAS/boards/{BOARD_ID}")
        return 0

    start = datetime(2026, 6, 15, 9, 0, 0)
    end = start + timedelta(days=21)
    sprint_body = {
        "name": SPRINT_NAME,
        "originBoardId": BOARD_ID,
        "goal": "Security closure + containerized Postgres. Exit: docker compose up, cookie auth, Fernet-only secrets.",
        "startDate": start.strftime("%Y-%m-%dT%H:%M:%S.000+0530"),
        "endDate": end.strftime("%Y-%m-%dT%H:%M:%S.000+0530"),
    }

    status, sprint = request("POST", f"{base_url}/rest/agile/1.0/sprint", auth, sprint_body)
    if status not in (200, 201):
        print("Failed to create sprint:", json.dumps(sprint, indent=2))
        return 1

    sprint_id = sprint.get("id")
    print(f"Created sprint {sprint_id}: {sprint.get('name')}")

    assign_status, assign_resp = request(
        "POST",
        f"{base_url}/rest/agile/1.0/sprint/{sprint_id}/issue",
        auth,
        {"issues": S1_STORIES},
    )
    if assign_status not in (200, 204):
        print("Failed to assign issues:", json.dumps(assign_resp, indent=2))
        return 1

    print("Assigned:", ", ".join(S1_STORIES))
    print(f"Board: {base_url}/jira/software/projects/CAS/boards/{BOARD_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
