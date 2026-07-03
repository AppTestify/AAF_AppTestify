#!/usr/bin/env python3
"""Create Jira epic + stories for UI Workspace Refinement (T-110–T-142)."""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOUD_BASE = "https://api.atlassian.com/ex/jira/a5ff7216-8c30-4859-812f-fec70776da1f"

EPIC_KEY = "CAS-129"  # created 2026-06-11; script skips epic if set and --stories-only
EPIC_SUMMARY = "UI Workspace Refinement — Dashboards, Reports & Design System"
EPIC_BODY = """4–6 week frontend initiative for Casantris workspace.

**Goals:**
- Unify workspace layout, buttons, tabs, and pagination
- Add Recharts dashboards to Command Center and Reports
- Polish Portfolio, Integrations, Brief, Settings, Onboarding

**Related:** CAS-100 (Phase 1 decision flow UI), CAS-115 (Phase 3 decision flow UI), CAS-53 (vitest frontend)

**Sprints:** UI-S1 through UI-S6 on board 134"""

STORIES: list[dict] = [
    {
        "task": "T-110",
        "summary": "WorkspacePageShell — unified page header/layout",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S1"],
        "body": """Create `frontend/src/components/layout/WorkspacePageShell.tsx` with `governance` and `operational` variants.

**Acceptance criteria:**
- Define `.workspace-page` CSS (max-width, padding aligned with `.app`)
- Migrate all `Workspace*Page.tsx` headers to shell
- Remove inline header duplication

**Files:** frontend/src/components/layout/WorkspacePageShell.tsx, frontend/src/pages/Workspace*Page.tsx""",
    },
    {
        "task": "T-111",
        "summary": "Button system — secondary, danger, icon variants",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S1"],
        "body": """Extend button hierarchy in split CSS module.

**Acceptance criteria:**
- `.btn-secondary`, `.btn-danger`, `.btn-icon` in `frontend/src/styles/buttons.css`
- One primary CTA per card/section rule documented

**Files:** frontend/src/App.css, frontend/src/styles/buttons.css""",
    },
    {
        "task": "T-112",
        "summary": "SegmentedTabs — unify settings/gov/tool-registry tabs",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S1"],
        "body": """Create shared `SegmentedTabs` component.

**Acceptance criteria:**
- Replace `settings-tabs`, `gov-tabs`, `tool-registry-tab`
- Used in Settings, Cases, GovernanceView, ToolRegistryTable

**Files:** frontend/src/components/ui/SegmentedTabs.tsx""",
    },
    {
        "task": "T-113",
        "summary": "PaginationBar — shared offset/page UX",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S1"],
        "body": """Create reusable pagination component.

**Acceptance criteria:**
- Shows "51–100 of 237" copy (not "Page offset")
- Page size 25/50/100; prev/next disabled states

**Files:** frontend/src/components/ui/PaginationBar.tsx""",
    },
    {
        "task": "T-114",
        "summary": "Data primitives — DataTable, SectionCard, KpiStrip, EmptyState",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S1"],
        "body": """Create shared UI primitives.

**Acceptance criteria:**
- Loading skeleton + empty CTA on list components
- Used by Reports + at least one list page

**Files:** frontend/src/components/ui/""",
    },
    {
        "task": "T-115",
        "summary": "CSS modularization — split App.css",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S1"],
        "body": """Split monolithic App.css into modules.

**Acceptance criteria:**
- `frontend/src/styles/` (tokens, layout, tables, charts, governance, buttons)
- App.css becomes import barrel; no visual regression on `/app/dashboard`

**Files:** frontend/src/styles/, frontend/src/App.css""",
    },
    {
        "task": "T-116",
        "summary": "Recharts dependency + ChartThemeProvider",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S2"],
        "body": """Add Recharts and theme wrapper.

**Acceptance criteria:**
- `recharts` in package.json
- Charts use CSS vars (`--accent`, `--good`, `--warn`, `--bad`)
- ResponsiveContainer wrapper

**Files:** frontend/package.json, frontend/src/components/charts/ChartTheme.tsx""",
    },
    {
        "task": "T-117",
        "summary": "Core chart components — RunStatus, CaseStatus, Connector, Consensus",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S2"],
        "body": """Build core dashboard charts.

**Acceptance criteria:**
- RunStatusDonut, CaseStatusBar, ConnectorHealthDonut, ConsensusGauge
- Data from fetchDashboardSummary(); aria-label + table fallback

**Files:** frontend/src/components/charts/""",
    },
    {
        "task": "T-118",
        "summary": "Command Center chart row above the fold",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S2"],
        "body": """Promote charts on Command Center.

**Acceptance criteria:**
- 3-chart row visible without expanding accordion
- KPI strip at top of WorkspaceHomePage

**Files:** frontend/src/pages/WorkspaceHomePage.tsx""",
    },
    {
        "task": "T-119",
        "summary": "Command Center layout restructure",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S2"],
        "body": """Restructure dashboard layout.

**Acceptance criteria:**
- Remove default-hidden "Advanced operations" accordion
- Incidents table + recommendation split retained

**Files:** frontend/src/pages/WorkspaceHomePage.tsx""",
    },
    {
        "task": "T-120",
        "summary": "useDashboardSummary shared hook",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S2"],
        "body": """Deduplicate dashboard API fetches.

**Acceptance criteria:**
- Shared hook used by Dashboard, Integrations, Evidence pages

**Files:** frontend/src/hooks/useDashboardSummary.ts""",
    },
    {
        "task": "T-121",
        "summary": "Reports tabbed layout",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S3"],
        "body": """Tabbed Reports hub.

**Acceptance criteria:**
- Tabs: Overview, Governance, Incidents, Audit, Exports via SegmentedTabs

**Files:** frontend/src/pages/WorkspaceReportsPage.tsx""",
    },
    {
        "task": "T-122",
        "summary": "Reports Overview charts",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S3"],
        "body": """Visual Overview tab.

**Acceptance criteria:**
- Replace "Operational distribution" table with donut/bar grid
- Executive portfolio KPIs in Overview tab

**Files:** frontend/src/pages/WorkspaceReportsPage.tsx, frontend/src/components/charts/""",
    },
    {
        "task": "T-123",
        "summary": "Reports Governance + Incidents tabs",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S3"],
        "body": """Governance and Incidents report tabs.

**Acceptance criteria:**
- Run outcomes, consensus, severity donut charts
- Keep IncidentFindingsPanel accordions

**Files:** frontend/src/pages/WorkspaceReportsPage.tsx""",
    },
    {
        "task": "T-124",
        "summary": "Reports Audit tab + date range filter",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S3"],
        "body": """Audit analytics tab.

**Acceptance criteria:**
- 7d/30d/90d date range filter
- Audit-by-area bar chart

**Files:** frontend/src/pages/WorkspaceReportsPage.tsx""",
    },
    {
        "task": "T-125",
        "summary": "Reports Exports tab polish",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S3"],
        "body": """Polish export UX.

**Acceptance criteria:**
- Export cards use SectionCard
- Primary=CSV, secondary=JSON; remove inline styles

**Files:** frontend/src/pages/WorkspaceReportsPage.tsx""",
    },
    {
        "task": "T-126",
        "summary": "API total counts for paginated lists",
        "labels": ["ui-refinement", "frontend", "backend", "sprint-UI-S4"],
        "body": """Paginated list API contract.

**Acceptance criteria:**
- Responses include `{ items, total, limit, offset }` for runs, cases, evidence, audit
- Frontend api.ts types updated

**Files:** app/routers/governance_v1.py, frontend/src/api.ts""",
    },
    {
        "task": "T-127",
        "summary": "Runs + Cases PaginationBar + URL sync",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S4"],
        "body": """Upgrade Runs and Cases pagination.

**Acceptance criteria:**
- `?page=2&page_size=50` in URL
- PaginationBar component; no "Page offset" copy

**Files:** WorkspaceRunsPage.tsx, WorkspaceCasesPage.tsx""",
    },
    {
        "task": "T-128",
        "summary": "Evidence pagination",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S4"],
        "body": """Paginate Evidence Hub.

**Acceptance criteria:**
- Uses offset param in fetchEvidence with PaginationBar

**Files:** frontend/src/pages/WorkspaceEvidencePage.tsx""",
    },
    {
        "task": "T-129",
        "summary": "Alerts + AuditTrail pagination",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S4"],
        "body": """Paginate audit-heavy pages.

**Acceptance criteria:**
- Alerts page paginates 200+ audit rows
- AuditTrailPanel supports pagination

**Files:** WorkspaceAlertsPage.tsx, AuditTrailPanel.tsx""",
    },
    {
        "task": "T-130",
        "summary": "Tool Registry pagination",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S4"],
        "body": """Paginate tool registry table.

**Acceptance criteria:**
- Client-side pages when status=all
- PaginationBar alongside scroll container

**Files:** frontend/src/components/governance/ToolRegistryTable.tsx""",
    },
    {
        "task": "T-131",
        "summary": "Portfolio lifecycle charts",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S5"],
        "body": """Portfolio visual analytics.

**Acceptance criteria:**
- Release status donut + confidence indicators from fetchExecutivePortfolioReport()

**Files:** frontend/src/pages/WorkspacePortfolioPage.tsx""",
    },
    {
        "task": "T-132",
        "summary": "Integrations health dashboard",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S5"],
        "body": """Integrations charts.

**Acceptance criteria:**
- Connector validation donut + timeline bar
- Uses useDashboardSummary hook

**Files:** frontend/src/pages/WorkspaceIntegrationsPage.tsx""",
    },
    {
        "task": "T-133",
        "summary": "Runs/Cases master-detail + sticky actions",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S5"],
        "body": """Standardize master-detail layout.

**Acceptance criteria:**
- 40/60 split pane
- Sticky action bar: Evidence, Brief, Export PDF, Share

**Files:** WorkspaceRunsPage.tsx, WorkspaceCasesPage.tsx""",
    },
    {
        "task": "T-134",
        "summary": "Brief page layout + print styles",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S5"],
        "body": """Executive Brief polish.

**Acceptance criteria:**
- Max 720px article column; print-friendly CSS
- Guardrail side panel

**Files:** frontend/src/pages/WorkspaceBriefPage.tsx""",
    },
    {
        "task": "T-135",
        "summary": "Settings refactor into tab modules",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S5"],
        "body": """Split monolithic Settings page.

**Acceptance criteria:**
- `pages/settings/*.tsx` tab modules
- `/app/ai-config` redirects to `?tab=ai`

**Files:** frontend/src/pages/WorkspaceSettingsPage.tsx, frontend/src/pages/settings/""",
    },
    {
        "task": "T-136",
        "summary": "Onboarding nav + CSS",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S5"],
        "body": """Onboarding discoverability.

**Acceptance criteria:**
- Sidebar link with first-run badge
- `.onboarding-page` CSS defined

**Files:** OnboardingWizardPage.tsx, WorkspaceShell.tsx""",
    },
    {
        "task": "T-137",
        "summary": "Runs timeseries API",
        "labels": ["ui-refinement", "backend", "sprint-UI-S6"],
        "body": """Backend timeseries endpoint.

**Acceptance criteria:**
- `GET /telemetry/runs-timeseries?days=7` returns daily counts by status

**Files:** app/routers/telemetry.py, frontend/src/api.ts""",
    },
    {
        "task": "T-138",
        "summary": "Advanced charts — RunsTrend, SloBurn, LlmCost",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S6"],
        "body": """Advanced dashboard charts.

**Acceptance criteria:**
- RunsTrendLine, SloBurnChart, LlmCostBar on Command Center
- Wire to timeseries + fetchObservabilitySummary()

**Files:** frontend/src/components/charts/, WorkspaceHomePage.tsx""",
    },
    {
        "task": "T-139",
        "summary": "Chart drill-down links",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S6"],
        "body": """Interactive chart navigation.

**Acceptance criteria:**
- Click chart slice navigates to filtered list (e.g. /app/runs?status=failed)

**Files:** frontend/src/components/charts/""",
    },
    {
        "task": "T-140",
        "summary": "Loading skeletons + a11y fixes",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S6"],
        "body": """Loading and accessibility polish.

**Acceptance criteria:**
- Skeleton on KPI cards and tables
- Replace Link.disabled hack in GovernanceView with real buttons

**Files:** frontend/src/components/ui/, GovernanceView.tsx""",
    },
    {
        "task": "T-141",
        "summary": "Frontend unit tests for UI primitives",
        "labels": ["ui-refinement", "frontend", "sprint-UI-S6"],
        "body": """Vitest coverage for new UI components.

**Acceptance criteria:**
- Tests for PaginationBar, chart data mappers, KpiStrip
- Extends CAS-53 vitest scope

**Files:** frontend/src/components/ui/*.test.tsx""",
    },
    {
        "task": "T-142",
        "summary": "Design doc — workspace UI refinement",
        "labels": ["ui-refinement", "docs", "sprint-UI-S6"],
        "body": """Document UI refinement architecture.

**Acceptance criteria:**
- docs/design/workspace-ui-refinement.md
- Documents shell, charts, pagination contract; links to epic

**Files:** docs/design/workspace-ui-refinement.md""",
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
            "labels": ["ui-refinement", "frontend", "workspace"],
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
    env = {**load_env(ROOT / ".env"), **os.environ}
    email = env.get("JIRA_EMAIL", "").strip()
    token = env.get("JIRA_API_TOKEN", "").strip()
    if not email or not token:
        print("Set JIRA_EMAIL and JIRA_API_TOKEN in .env", file=sys.stderr)
        return 1

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    epic_key = create_epic(auth)
    print(f"Created epic {epic_key}: {EPIC_SUMMARY}")

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
