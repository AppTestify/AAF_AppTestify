#!/usr/bin/env python3
"""Create Jira epic + stories for Reports, Notifications & Platform Email (T-143–T-161)."""

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

EPIC_KEY = "CAS-163"  # created 2026-06-12 via MCP; use --stories-only to add more
EPIC_SUMMARY = "Reporting, Notifications & Platform Email"
EPIC_BODY = """Post-UI initiative for Casantris workspace report exports, platform SMTP, Slack/Teams, and scheduled digests.

**Goals:**
- Excel/PDF report exports for runs, audit, portfolio
- Platform SMTP default with tenant override + 12+ HTML templates
- Unified notification router (email, Slack, Teams)
- On-demand and scheduled report email digests

**Related:** CAS-129 (UI workspace refinement), CAS-115 (Phase 3 decision flow UI)

**Sprints:** R1–R4 on board 134"""

STORIES: list[dict] = [
    {
        "task": "T-143",
        "summary": "Report catalog + export contract",
        "labels": ["reports", "notifications", "platform-email", "sprint-R1"],
        "body": """Define report export catalog and API contract.

**Acceptance criteria:**
- `docs/design/report-export-catalog.md` documents report types × formats
- Extend `app/routers/reports.py` `format` enum for xlsx|pdf

**Files:** docs/design/report-export-catalog.md, app/routers/reports.py""",
    },
    {
        "task": "T-144",
        "summary": "Excel/XLSX export engine",
        "labels": ["reports", "notifications", "platform-email", "sprint-R1"],
        "body": """Build Excel export service with openpyxl.

**Acceptance criteria:**
- `app/services/report_xlsx.py` with Summary + Data sheets
- Portfolio: Projects, Releases, Summary sheets
- Add `openpyxl` to requirements.txt

**Files:** app/services/report_xlsx.py, requirements.txt""",
    },
    {
        "task": "T-145",
        "summary": "Multi-report PDF builders",
        "labels": ["reports", "notifications", "platform-email", "sprint-R1"],
        "body": """Build PDF export service for multi-report bundles.

**Acceptance criteria:**
- `app/services/report_pdf.py` for runs summary, audit, executive portfolio
- Branded header: tenant name, generated_at, report type
- Extend ReportLab patterns from df_onepager_pdf.py

**Files:** app/services/report_pdf.py, app/services/df_onepager_pdf.py""",
    },
    {
        "task": "T-146",
        "summary": "Reports API — xlsx/pdf endpoints",
        "labels": ["reports", "notifications", "platform-email", "sprint-R1"],
        "body": """Extend reports router with xlsx/pdf format support.

**Acceptance criteria:**
- `GET /reports/runs/summary?format=xlsx|pdf`
- `GET /reports/audit-events?format=xlsx|pdf`
- `GET /reports/portfolio/executive?format=xlsx|pdf`

**Files:** app/routers/reports.py""",
    },
    {
        "task": "T-147",
        "summary": "Frontend Exports tab — Excel/PDF buttons",
        "labels": ["reports", "notifications", "platform-email", "frontend", "sprint-R1"],
        "body": """Add Excel/PDF download buttons to Reports Exports tab.

**Acceptance criteria:**
- WorkspaceReportsPage Exports tab: Excel + PDF per report card
- api.ts helpers for blob download with format param

**Files:** frontend/src/pages/WorkspaceReportsPage.tsx, frontend/src/api.ts""",
    },
    {
        "task": "T-148",
        "summary": "PlatformNotificationConfig model + migration",
        "labels": ["reports", "notifications", "platform-email", "sprint-R2"],
        "body": """Add platform-level notification configuration model.

**Acceptance criteria:**
- PlatformNotificationConfig in app/models/config.py
- Alembic migration for platform SMTP + template defaults
- Fields: smtp_host, smtp_port, from_address, templates_json

**Files:** app/models/config.py, alembic/versions/""",
    },
    {
        "task": "T-149",
        "summary": "Platform notifications API (superadmin only)",
        "labels": ["reports", "notifications", "platform-email", "sprint-R2"],
        "body": """Superadmin API for platform notification settings.

**Acceptance criteria:**
- `app/routers/platform_config.py`: GET/PUT `/platform/notifications`
- Test SMTP endpoint for superadmin
- Auth guard: is_superadmin only

**Files:** app/routers/platform_config.py""",
    },
    {
        "task": "T-150",
        "summary": "SMTP resolution — platform default, tenant override",
        "labels": ["reports", "notifications", "platform-email", "sprint-R2"],
        "body": """Resolve SMTP config: platform default, tenant override.

**Acceptance criteria:**
- `app/services/smtp_resolver.py` with resolve_smtp_config(tenant_id)
- email_runtime.py uses resolver for all outbound mail

**Files:** app/services/smtp_resolver.py, app/services/email_runtime.py""",
    },
    {
        "task": "T-151",
        "summary": "Full template catalog + HTML email",
        "labels": ["reports", "notifications", "platform-email", "sprint-R2"],
        "body": """Expand email template catalog with HTML multipart.

**Acceptance criteria:**
- 12+ template keys (user_welcome, governance_run_complete, report_digest_daily, etc.)
- send_html_templated_email() with body_text + body_html
- {{variable}} placeholders documented

**Files:** app/services/email_runtime.py""",
    },
    {
        "task": "T-152",
        "summary": "Superadmin Platform Settings UI",
        "labels": ["reports", "notifications", "platform-email", "frontend", "sprint-R2"],
        "body": """Superadmin platform settings page for SMTP and templates.

**Acceptance criteria:**
- WorkspacePlatformSettingsPage at /app/platform-settings
- Nav in WorkspaceShell for is_superadmin
- SMTP fields, test connection, template editor grid

**Files:** frontend/src/pages/WorkspacePlatformSettingsPage.tsx, WorkspaceShell.tsx""",
    },
    {
        "task": "T-153",
        "summary": "Teams incoming webhook support",
        "labels": ["reports", "notifications", "platform-email", "sprint-R3"],
        "body": """Add Microsoft Teams incoming webhook delivery.

**Acceptance criteria:**
- teams_incoming_webhook_encrypted on TenantNotificationConfig + PlatformNotificationConfig
- app/services/teams_notifier.py with adaptive card style messages

**Files:** app/models/config.py, app/services/teams_notifier.py""",
    },
    {
        "task": "T-154",
        "summary": "Enhanced Slack notifier",
        "labels": ["reports", "notifications", "platform-email", "sprint-R3"],
        "body": """Rich Slack Block Kit messages from templates.

**Acceptance criteria:**
- app/services/slack_notifier.py with block-style messages
- Template-driven formatting for run complete/failed events

**Files:** app/services/slack_notifier.py""",
    },
    {
        "task": "T-155",
        "summary": "Unified notification router",
        "labels": ["reports", "notifications", "platform-email", "sprint-R3"],
        "body": """Central notification delivery router.

**Acceptance criteria:**
- app/services/notification_router.py routes email/slack/teams
- Refactor governance_delivery.py to use router
- Events: run complete/failed, case created, audit critical

**Files:** app/services/notification_router.py, app/services/governance_delivery.py""",
    },
    {
        "task": "T-156",
        "summary": "Tenant notification settings UI — Teams + toggles",
        "labels": ["reports", "notifications", "platform-email", "frontend", "sprint-R3"],
        "body": """Expand tenant notification settings in Users tab.

**Acceptance criteria:**
- UsersTab: Teams webhook field
- Per-channel enable flags (email/slack/teams)
- "Using platform SMTP" badge when no tenant override

**Files:** frontend/src/pages/settings/UsersTab.tsx""",
    },
    {
        "task": "T-157",
        "summary": 'On-demand "Email this report" API',
        "labels": ["reports", "notifications", "platform-email", "sprint-R4"],
        "body": """API to email reports on demand with attachments.

**Acceptance criteria:**
- POST /reports/email with report_type, format, recipients[]
- Attaches XLSX or PDF via notification router + report_on_demand template

**Files:** app/routers/reports.py, app/services/notification_router.py""",
    },
    {
        "task": "T-158",
        "summary": "Reports UI — Email report modal",
        "labels": ["reports", "notifications", "platform-email", "frontend", "sprint-R4"],
        "body": """Email report modal on Exports tab.

**Acceptance criteria:**
- Recipient input, format picker, Send button
- Success/error toast on POST /reports/email

**Files:** frontend/src/pages/WorkspaceReportsPage.tsx""",
    },
    {
        "task": "T-159",
        "summary": "Digest schedule config per tenant",
        "labels": ["reports", "notifications", "platform-email", "sprint-R4"],
        "body": """Per-tenant digest schedule configuration.

**Acceptance criteria:**
- digest_schedule_json on TenantNotificationConfig
- Daily time (UTC), weekly day, recipient list
- Settings UI fields in UsersTab

**Files:** app/models/config.py, frontend/src/pages/settings/UsersTab.tsx""",
    },
    {
        "task": "T-160",
        "summary": "Celery beat — daily + weekly digest jobs",
        "labels": ["reports", "notifications", "platform-email", "sprint-R4"],
        "body": """Scheduled report digest background jobs.

**Acceptance criteria:**
- app/tasks/report_digests.py with send_tenant_digest()
- Celery beat schedule in celery_app.py for daily + weekly
- Uses report_digest_daily/weekly templates

**Files:** app/celery_app.py, app/tasks/report_digests.py""",
    },
    {
        "task": "T-161",
        "summary": "Tests + design doc",
        "labels": ["reports", "notifications", "platform-email", "docs", "sprint-R4"],
        "body": """Tests and architecture documentation.

**Acceptance criteria:**
- tests/test_report_exports.py
- tests/test_platform_notifications.py
- docs/design/reports-notifications.md

**Files:** tests/, docs/design/reports-notifications.md""",
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


def create_epic(auth: str) -> str:
    payload = {
        "fields": {
            "project": {"key": "CAS"},
            "issuetype": {"name": "Epic"},
            "summary": EPIC_SUMMARY,
            "description": EPIC_BODY,
            "labels": ["reports", "notifications", "platform-email", "integrations"],
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
