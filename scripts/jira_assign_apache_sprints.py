#!/usr/bin/env python3
"""Assign Apache OSS scalability stories (T-192–T-211) to sprint labels on board 134."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD_BASE = "https://api.atlassian.com/ex/jira/a5ff7216-8c30-4859-812f-fec70776da1f"

SPRINT_LABELS = {
    "S0": ["T-192", "T-193", "T-194"],
    "S1": ["T-195", "T-196", "T-197", "T-198"],
    "S2": ["T-199", "T-200", "T-201", "T-202"],
    "S3": ["T-203", "T-204", "T-205"],
    "S4": ["T-206", "T-207", "T-208", "T-209"],
    "S5": ["T-210", "T-211"],
}


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def jql_search(auth: str, jql: str) -> list[dict]:
    url = f"{CLOUD_BASE}/rest/api/3/search?jql={urllib.request.quote(jql)}&maxResults=50"
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    return data.get("issues", [])


def add_labels(auth: str, issue_key: str, labels: list[str]) -> None:
    payload = {"update": {"labels": [{"add": label} for label in labels]}}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{CLOUD_BASE}/rest/api/3/issue/{issue_key}",
        data=data,
        method="PUT",
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req):
            pass
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Failed {issue_key}: {exc.read().decode()}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epic", default="", help="Epic key filter, e.g. CAS-222")
    args = parser.parse_args()

    env = {**load_env(ROOT / ".env"), **os.environ}
    email = env.get("JIRA_EMAIL", "").strip()
    token = env.get("JIRA_API_TOKEN", "").strip()
    if not email or not token:
        print("Set JIRA_EMAIL and JIRA_API_TOKEN", file=sys.stderr)
        return 1

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    jql = 'project = CAS AND summary ~ "T-19" ORDER BY key ASC'
    if args.epic:
        jql = f'project = CAS AND parent = {args.epic} ORDER BY key ASC'

    issues = jql_search(auth, jql)
    if not issues:
        print("No matching issues found. Run jira_create_apache_scalability.py first.", file=sys.stderr)
        return 1

    for issue in issues:
        key = issue["key"]
        summary = issue["fields"]["summary"]
        task_id = summary.split(":", 1)[0].strip()
        sprint_label = None
        for sprint, tasks in SPRINT_LABELS.items():
            if task_id in tasks:
                sprint_label = f"sprint-{sprint}"
                break
        if not sprint_label:
            continue
        add_labels(auth, key, [sprint_label, "apache-oss", "board-134"])
        print(f"Labeled {key} ({task_id}) → {sprint_label}")

    print("Sprint assignment complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
