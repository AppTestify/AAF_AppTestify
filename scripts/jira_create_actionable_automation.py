#!/usr/bin/env python3
"""Create Jira epic + stories for Actionable Automation (T-180–T-191)."""

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

EPIC_KEY = "CAS-202"  # Actionable Automation epic
EPIC_SUMMARY = "Actionable Automation — Execute Governance Decisions"
EPIC_BODY = """Close the last mile: Casantris executes approved governance decisions.

**Goals:**
- Create Jira blockers when HOLD_RELEASE / PATCH_BLOCK_RELEASE is approved
- Trigger hold-release workflow (portfolio hold, workflow run, notifications, webhook)
- Track execution in decision_actions with full audit trail
- Tenant automation settings (dry-run, require approval)
- UI execute button on governance decisions

**Gap:** Competitor matrix marks Actionable automation as missing — Casantris recommends but does not execute.

**Related:** CAS-183 (HOLD_RELEASE action), decision_actions table, GovernanceWorkflowRun

**Design:** docs/design/actionable-automation.md

**Sprints:** A1–A4 on board 134"""

STORIES: list[dict] = [
    {
        "task": "T-180",
        "summary": "Action automation service + action catalog",
        "labels": ["actionable-automation", "governance", "sprint-A1"],
        "body": """Core orchestration for governance action execution.

**Acceptance criteria:**
- app/services/action_automation.py maps hold_release → [jira_blocker, hold_release_workflow]
- Creates DecisionAction rows (pending → running → succeeded|failed)
- Reads automation config from TenantSettings.ui_preferences.action_automation

**Files:** app/services/action_automation.py""",
    },
    {
        "task": "T-181",
        "summary": "tools/pm/create_blocker — Jira issue creation",
        "labels": ["actionable-automation", "jira", "sprint-A1"],
        "body": """Write path for Jira connector.

**Acceptance criteria:**
- tools/pm/create_blocker.py creates Bug/Task via POST /rest/api/3/issue
- Sim mode returns SIM-{n} key without API call
- jira_post accepts 201 Created

**Files:** tools/pm/create_blocker.py, tools/jira_client.py""",
    },
    {
        "task": "T-182",
        "summary": "Jira blocker executor + tests",
        "labels": ["actionable-automation", "jira", "sprint-A1"],
        "body": """Executor wrapping create_blocker for decision actions.

**Acceptance criteria:**
- app/services/action_executors/jira_blocker.py
- Issue summary includes run id, action, consensus score
- tests/test_action_automation.py with mocked Jira

**Files:** app/services/action_executors/jira_blocker.py, tests/""",
    },
    {
        "task": "T-183",
        "summary": "Hold-release workflow executor",
        "labels": ["actionable-automation", "workflow", "sprint-A2"],
        "body": """Portfolio + workflow effects for hold_release.

**Acceptance criteria:**
- Sets ProjectRelease.release_decision=hold, status=on_hold when linked
- Creates GovernanceWorkflowRun workflow_type=hold_release
- Audit event + optional outbound webhook POST

**Files:** app/services/action_executors/hold_release.py""",
    },
    {
        "task": "T-184",
        "summary": "Wire execution into decision approval",
        "labels": ["actionable-automation", "api", "sprint-A2"],
        "body": """Auto-execute on approve when automation enabled.

**Acceptance criteria:**
- approve_decision calls queue_decision_actions when action_automation.enabled
- Respects require_approval and dry_run flags

**Files:** app/routers/governance_v1.py""",
    },
    {
        "task": "T-185",
        "summary": "Async execution via Celery (optional path)",
        "labels": ["actionable-automation", "celery", "sprint-A2"],
        "body": """Background task for action execution with retry.

**Acceptance criteria:**
- Celery task execute_decision_actions when broker configured
- Sync fallback when Redis absent (dev)

**Files:** app/celery_app.py, app/tasks/action_automation.py""",
    },
    {
        "task": "T-186",
        "summary": "Execute-actions API endpoints",
        "labels": ["actionable-automation", "api", "sprint-A3"],
        "body": """Manual trigger and status polling.

**Acceptance criteria:**
- POST /governance/decisions/{id}/execute-actions
- GET /governance/decisions/{id}/actions
- POST /governance/runs/{id}/execute-actions

**Files:** app/routers/governance_v1.py""",
    },
    {
        "task": "T-187",
        "summary": "Automation settings in tenant config API",
        "labels": ["actionable-automation", "settings", "sprint-A3"],
        "body": """Expose action_automation block in tenant settings.

**Acceptance criteria:**
- GET/PATCH tenant settings includes action_automation defaults
- Validation: webhook URL https only in prod

**Files:** app/routers/tenant_config.py""",
    },
    {
        "task": "T-188",
        "summary": "Automation settings UI (Settings tab)",
        "labels": ["actionable-automation", "ui", "sprint-A3"],
        "body": """Tenant admin toggles for automation.

**Acceptance criteria:**
- Settings → Automation: enable, dry-run, Jira blocker, hold workflow, webhook URL
- Help text explains approval gate

**Files:** frontend/src/pages/WorkspaceSettingsPage.tsx or AutomationTab""",
    },
    {
        "task": "T-189",
        "summary": "Execute button on governance decision panel",
        "labels": ["actionable-automation", "ui", "sprint-A4"],
        "body": """One-click execute from run/decision view.

**Acceptance criteria:**
- ConsensusDecisionPanel shows Execute when action is hold_release
- Displays DecisionAction status chips (pending/succeeded/failed)

**Files:** frontend ConsensusDecisionPanel, api.ts""",
    },
    {
        "task": "T-190",
        "summary": "Integration tests + sim mode validation",
        "labels": ["actionable-automation", "testing", "sprint-A4"],
        "body": """End-to-end automation tests.

**Acceptance criteria:**
- Approve hold_release → decision_actions populated in sim mode
- Dry-run does not call external APIs

**Files:** tests/test_action_automation.py""",
    },
    {
        "task": "T-191",
        "summary": "Runbook + tool registry entry for create_blocker",
        "labels": ["actionable-automation", "docs", "sprint-A4"],
        "body": """Operational documentation.

**Acceptance criteria:**
- docs/runbooks/actionable-automation.md
- data/tool_registry.json entry for create_blocker

**Files:** docs/, data/tool_registry.json""",
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
            payload = json.loads(raw) if raw else {"error": str(exc)}
        except json.JSONDecodeError:
            payload = {"error": raw or str(exc)}
        return exc.code, payload


def create_epic(auth: str) -> str:
    payload = {
        "fields": {
            "project": {"key": "CAS"},
            "issuetype": {"name": "Epic"},
            "summary": EPIC_SUMMARY,
            "description": EPIC_BODY,
            "labels": ["actionable-automation", "governance", "execution"],
        }
    }
    status, result = request("POST", f"{CLOUD_BASE}/rest/api/3/issue", auth, payload)
    if status not in (200, 201):
        raise RuntimeError(f"Failed epic: {status} {result}")
    return result["key"]


def create_story(auth: str, epic_key: str, *, task: str, summary: str, body: str, labels: list[str]) -> str:
    payload = {
        "fields": {
            "project": {"key": "CAS"},
            "issuetype": {"name": "Story"},
            "summary": f"{task}: {summary}",
            "description": body,
            "parent": {"key": epic_key},
            "labels": labels,
        }
    }
    status, result = request("POST", f"{CLOUD_BASE}/rest/api/3/issue", auth, payload)
    if status not in (200, 201):
        raise RuntimeError(f"Failed {task}: {status} {result}")
    return result["key"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stories-only", action="store_true", help="Skip epic creation; use EPIC_KEY")
    args = parser.parse_args()

    env = {**load_env(ROOT / ".env"), **os.environ}
    email = env.get("JIRA_EMAIL", "").strip()
    token = env.get("JIRA_API_TOKEN", "").strip()
    if not email or not token:
        print("Set JIRA_EMAIL and JIRA_API_TOKEN in .env", file=sys.stderr)
        return 1

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    epic_key = EPIC_KEY
    if not args.stories_only:
        epic_key = create_epic(auth)
        print(f"Created epic {epic_key}: {EPIC_SUMMARY}")
        print(f"Update EPIC_KEY = \"{epic_key}\" in this script for --stories-only reruns")
    elif not epic_key:
        print("Set EPIC_KEY or omit --stories-only", file=sys.stderr)
        return 1
    else:
        print(f"Using epic {epic_key}: {EPIC_SUMMARY}")

    created: list[str] = []
    for story in STORIES:
        key = create_story(
            auth,
            epic_key,
            task=story["task"],
            summary=story["summary"],
            body=story["body"],
            labels=story["labels"],
        )
        created.append(key)
        print(f"Created {key}: {story['task']} {story['summary']}")

    print(f"\nDone — epic {epic_key} + {len(created)} stories")
    print("Story keys:", ", ".join(created))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
