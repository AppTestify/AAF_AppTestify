#!/usr/bin/env python3
"""Assign Actionable Automation stories (CAS-202) to sprints A1–A4 on board 134."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD_BASE = "https://api.atlassian.com/ex/jira/a5ff7216-8c30-4859-812f-fec70776da1f"
BOARD_ID = 134

# Set after running jira_create_actionable_automation.py
EPIC_KEY = "CAS-202"
STORY_KEYS: list[str] = []

SPRINTS = [
    {
        "name": "A1 — Automation foundation",
        "goal": "Action automation service, Jira create_blocker, blocker executor.",
        "tasks": ["T-180", "T-181", "T-182"],
    },
    {
        "name": "A2 — Hold-release workflow",
        "goal": "Hold-release executor, decision approval wiring, Celery task.",
        "tasks": ["T-183", "T-184", "T-185"],
    },
    {
        "name": "A3 — API + settings",
        "goal": "Execute-actions endpoints, tenant automation settings, settings UI.",
        "tasks": ["T-186", "T-187", "T-188"],
    },
    {
        "name": "A4 — UI execute + tests",
        "goal": "Execute button, integration tests, runbook.",
        "tasks": ["T-189", "T-190", "T-191"],
    },
]


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def request(method: str, url: str, auth: str, payload: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode() if payload is not None else None
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
            body = json.loads(raw) if raw else {"error": str(exc)}
        except json.JSONDecodeError:
            body = {"error": raw or str(exc)}
        return exc.code, body


def fetch_story_keys_by_task(auth: str, epic_key: str) -> dict[str, str]:
    jql = f'parent = {epic_key} ORDER BY key ASC'
    status, result = request(
        "GET",
        f"{CLOUD_BASE}/rest/api/3/search/jql?jql={urllib.parse.quote(jql)}&maxResults=50&fields=summary",
        auth,
    )
    if status != 200:
        raise RuntimeError(f"JQL search failed: {status} {result}")
    mapping: dict[str, str] = {}
    for issue in result.get("issues", []):
        summary = issue.get("fields", {}).get("summary", "")
        for task in [f"T-{n}" for n in range(180, 192)]:
            if summary.startswith(f"{task}:"):
                mapping[task] = issue["key"]
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epic", default=EPIC_KEY, help="Epic key e.g. CAS-202")
    args = parser.parse_args()

    env = {**load_env(ROOT / ".env"), **os.environ}
    email = env.get("JIRA_EMAIL", "").strip()
    token = env.get("JIRA_API_TOKEN", "").strip()
    if not email or not token:
        print("Set JIRA_EMAIL and JIRA_API_TOKEN in .env", file=sys.stderr)
        return 1

    epic_key = args.epic.strip()
    if not epic_key:
        print("Pass --epic CAS-XXX", file=sys.stderr)
        return 1

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    task_to_key = fetch_story_keys_by_task(auth, epic_key)
    if not task_to_key:
        print(f"No stories found under {epic_key}", file=sys.stderr)
        return 1

    base_url = f"{CLOUD_BASE}/rest/agile/1.0"
    for sprint in SPRINTS:
        status, created = request(
            "POST",
            f"{base_url}/board/{BOARD_ID}/sprint",
            auth,
            {"name": sprint["name"], "goal": sprint["goal"]},
        )
        if status not in (200, 201):
            raise RuntimeError(f"Create sprint failed: {status} {created}")
        sprint_id = created["id"]
        issue_keys = [task_to_key[t] for t in sprint["tasks"] if t in task_to_key]
        if issue_keys:
            st, res = request(
                "POST",
                f"{base_url}/sprint/{sprint_id}/issue",
                auth,
                {"issues": issue_keys},
            )
            if st not in (200, 204):
                raise RuntimeError(f"Assign sprint failed: {st} {res}")
        print(f"Sprint {sprint_id} {sprint['name']}: {', '.join(issue_keys)}")

    print(f"\nDone — epic {epic_key} stories assigned to A1–A4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
