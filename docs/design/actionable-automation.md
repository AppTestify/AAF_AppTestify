# Actionable Automation — Design

Casantris today recommends actions (`HOLD_RELEASE`, `PATCH_BLOCK_RELEASE`) but does not execute them. This epic closes the last mile: approved governance decisions trigger real-world effects.

## Problem

| Today | Target |
|-------|--------|
| Pipeline outputs `hold_release` | Jira blocker created, release held in portfolio |
| Decision approved in UI | Teams/Slack notified, webhook fired to CI/CD |
| `DecisionAction` table exists but unused | Every action tracked with state + audit trail |
| Jira connector is read-only | `create_blocker` writes issues in live mode |

## Architecture

```
Governance Run (HOLD_RELEASE)
        │
        ▼
Decision proposed → approved (decisions.approve)
        │
        ▼
action_automation.queue_decision_actions()
        │
        ├── jira_blocker      → POST /rest/api/3/issue
        ├── hold_release_workflow → ProjectRelease.hold + GovernanceWorkflowRun
        └── outbound_webhook  → POST tenant webhook URL (optional)
```

## Tenant configuration

Stored in `TenantSettings.ui_preferences.action_automation`:

```json
{
  "enabled": true,
  "dry_run": false,
  "require_approval": true,
  "jira_blocker_enabled": true,
  "hold_release_workflow_enabled": true,
  "hold_release_webhook_url": "https://hooks.example.com/hold-release"
}
```

- `require_approval: true` (default) — actions run only after `POST /decisions/{id}/approve`
- `dry_run: true` — record `DecisionAction` as `simulated` without external calls

## Action catalog

| Governance action | Executed steps |
|-------------------|----------------|
| `hold_release` | Jira blocker + hold-release workflow + optional webhook |
| `patch_block_release` | Jira blocker |

## API

| Method | Path | Permission |
|--------|------|------------|
| POST | `/api/v1/governance/decisions/{id}/execute-actions` | `decisions.approve` |
| GET | `/api/v1/governance/decisions/{id}/actions` | `cases.manage` |
| POST | `/api/v1/governance/runs/{id}/execute-actions` | `decisions.approve` |

## Sprint breakdown (Jira CAS-202)

| Sprint | Stories | Focus |
|--------|---------|-------|
| A1 | T-180–T-182 | Automation service + Jira create blocker |
| A2 | T-183–T-185 | Hold-release workflow + decision approval wiring |
| A3 | T-186–T-188 | API endpoints + automation settings UI |
| A4 | T-189–T-191 | Execute button in governance UI + tests + runbook |

## Success criteria

1. Approving a `hold_release` decision creates a Jira issue (or sim key) and marks portfolio release `on_hold`.
2. All steps appear in `decision_actions` with `pending → running → succeeded|failed`.
3. Dry-run mode never calls Jira or webhooks.
4. Audit events recorded for each execution.
