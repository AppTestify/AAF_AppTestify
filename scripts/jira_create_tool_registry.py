#!/usr/bin/env python3
"""Create Jira stories for the full AgileOps tool registry (tool_registry_full.html)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EPIC_KEY = "CAS-71"
CLOUD_BASE = "https://api.atlassian.com/ex/jira/a5ff7216-8c30-4859-812f-fec70776da1f"

STORIES: list[dict] = [
    {
        "task": "T-057",
        "summary": "get_pr_status() — DevOps agent tool",
        "labels": ["tool-registry", "devops-agent", "T-057", "sprint-S4"],
        "body": """Implement `get_pr_status()` per tool registry.

**Agent:** DevOps | **Method:** API + MCP (Phase 3)
**System:** GitHub Pull Requests — Bearer token repo scope
**API:** `GET /repos/{owner}/{repo}/pulls?state=open&base={release_branch}`; `GET .../pulls/{pr}/reviews`
**Returns:** open_pr_count, approved_count, changes_requested_count, draft_pr_flag, oldest_open_pr_days
**Fires:** Feature flag rollout and freeze window checks

**PM scenario:** Enable checkout flag for 10% — are all PRs merged?

**Acceptance criteria:**
- `tools/devops/pr_status.py` with sim + live GitHub paths
- Registered in `agents/devops.py` tool list and weights
- Normalized `ToolResult` with registry fields
- Unit test with fixture JSON""",
    },
    {
        "task": "T-058",
        "summary": "get_commit_activity() — DevOps agent tool",
        "labels": ["tool-registry", "devops-agent", "T-058", "sprint-S4"],
        "body": """Implement `get_commit_activity()` per tool registry.

**Agent:** DevOps | **Method:** Direct API
**System:** GitHub Commits — Bearer token repo scope
**API:** `GET /repos/{owner}/{repo}/commits?sha={branch}&since={24h_ago}`; `GET .../compare/{base}...{head}`
**Returns:** commit_count_24h, files_changed, lines_added, lines_deleted, authors_count, high_risk_path_touched
**Fires:** Hotfix and large-change risk assessments

**PM scenario:** Small hotfix — how much actually changed?

**Acceptance criteria:**
- `tools/devops/commit_activity.py` with sim + live paths
- High-risk path detection (payment/, auth/)
- Wired into DevOps agent; unit tests""",
    },
    {
        "task": "T-059",
        "summary": "check_pipeline_config() — DevOps agent tool",
        "labels": ["tool-registry", "devops-agent", "T-059", "sprint-S4"],
        "body": """Implement `check_pipeline_config()` per tool registry.

**Agent:** DevOps | **Method:** Direct API
**System:** GitHub Actions — Bearer token repo scope
**API:** `GET /repos/{owner}/{repo}/contents/.github/workflows`; parse YAML for approval gates
**Returns:** pipeline_has_approval_gate, environments_protected[], manual_gate_configured, freeze_window_active (workspace config)
**Fires:** Freeze window and compliance governance runs

**PM scenario:** Can we deploy during quarter-end freeze?

**Acceptance criteria:**
- `tools/devops/pipeline_config.py` parses workflow YAML
- Reads freeze_window from tenant/workspace settings
- Wired into DevOps agent; unit tests""",
    },
    {
        "task": "T-060",
        "summary": "get_story_cycle_time() — PM agent tool",
        "labels": ["tool-registry", "pm-agent", "T-060", "sprint-S4"],
        "body": """Implement `get_story_cycle_time()` per tool registry.

**Agent:** PM | **Method:** Direct API
**System:** Jira REST API v3 — email + API token
**API:** JQL active sprint Done stories; `GET /rest/api/3/issue/{key}/changelog`
**Returns:** avg_cycle_time_days, cycle_time_trend, stories_stuck_in_review (3+ days), longest_cycle_time_story
**Fires:** Leadership reporting and delivery trend analysis

**Acceptance criteria:**
- `tools/pm/story_cycle_time.py` using `tools/jira_client.py`
- Changelog-based In Progress → Done duration
- Wired into PM agent; unit tests""",
    },
    {
        "task": "T-061",
        "summary": "get_scope_change() — PM agent tool",
        "labels": ["tool-registry", "pm-agent", "T-061", "sprint-S4"],
        "body": """Implement `get_scope_change()` per tool registry.

**Agent:** PM | **Method:** Direct API + AgileOps DB
**System:** Jira Agile API + sprint_start_snapshot in DB
**API:** `GET /rest/agile/1.0/sprint/{sprintId}/issue`; compare vs snapshot at sprint start
**Returns:** stories_added_after_start, points_added_after_start, scope_change_pct, sprint_start_vs_current_commitment
**Fires:** When velocity is low and cause is unclear

**Acceptance criteria:**
- Sprint snapshot model/migration for scope baseline
- `tools/pm/scope_change.py` computes mid-sprint delta
- Wired into PM agent; unit tests""",
    },
    {
        "task": "T-062",
        "summary": "get_team_capacity() — PM agent tool (Roadmap)",
        "labels": ["tool-registry", "pm-agent", "T-062", "roadmap", "sprint-S6"],
        "body": """Implement `get_team_capacity()` per tool registry (**Roadmap**).

**Agent:** PM | **Method:** Roadmap
**System:** Jira/Tempo Timesheets OAuth2 OR manual capacity in workspace settings
**API:** Tempo `GET /4/worklogs/user/{accountId}` or workspace capacity config
**Returns:** team_capacity_pct, planned_vs_available_hours, at_risk_stories, leave_count_this_sprint

**PM scenario:** 3 people on leave — is the sprint still achievable?

**Acceptance criteria:**
- Workspace capacity settings UI + API
- Optional Tempo connector integration
- Capacity-adjusted risk signal in PM agent""",
    },
    {
        "task": "T-063",
        "summary": "get_cost_by_tag() — FinOps agent tool",
        "labels": ["tool-registry", "finops-agent", "T-063", "sprint-S5"],
        "body": """Implement `get_cost_by_tag()` per tool registry.

**Agent:** FinOps | **Method:** Direct API
**System:** AWS Cost Explorer — IAM ce:GetCostAndUsage
**API:** `POST ce.amazonaws.com → GetCostAndUsage` GroupBy TAG(Team/Service/Environment)
**Returns:** cost_by_team_tag[], cost_by_service_tag[], cost_by_environment, untagged_resource_cost, top_spending_team
**Fires:** Team-level accountability and sprint cost governance

**Acceptance criteria:**
- `tools/finops/cost_by_tag.py` with sim + live AWS paths
- Tagging policy validation in workspace settings
- Wired into FinOps agent; unit tests""",
    },
    {
        "task": "T-064",
        "summary": "get_cost_forecast() — FinOps agent tool (Roadmap)",
        "labels": ["tool-registry", "finops-agent", "T-064", "roadmap", "sprint-S6"],
        "body": """Implement `get_cost_forecast()` per tool registry (**Roadmap**).

**Agent:** FinOps | **Method:** Roadmap
**System:** AWS Cost Explorer — IAM ce:GetCostForecast
**API:** `POST ce.amazonaws.com → GetCostForecast` (30d, 95% CI)
**Returns:** forecast_spend_usd, confidence_interval, forecast_vs_budget_delta, primary_cost_driver_forecast

**Acceptance criteria:**
- `tools/finops/cost_forecast.py` with AWS GetCostForecast
- CFO/board reporting integration in governance output""",
    },
    {
        "task": "T-065",
        "summary": "check_ssl_expiry() — DevSecOps agent tool",
        "labels": ["tool-registry", "devsecops-agent", "T-065", "sprint-S5"],
        "body": """Implement `check_ssl_expiry()` per tool registry.

**Agent:** DevSecOps | **Method:** Direct API
**System:** AgileOps TLS checker + AWS Certificate Manager
**API:** `ssl.get_server_certificate()` on workspace domains; ACM ListCertificates/DescribeCertificate
**Returns:** cert_expiry_date, days_remaining, affected_domains[], issuer, renewal_status, acm_managed
**Fires:** Every release governance run for payment/auth services

**Acceptance criteria:**
- `tools/devsecops/ssl_expiry.py` with domain list from tenant settings
- Optional ACM integration for managed certs
- HOLD recommendation when days_remaining < 7; unit tests""",
    },
    {
        "task": "T-066",
        "summary": "get_sast_results() — DevSecOps agent tool (Roadmap)",
        "labels": ["tool-registry", "devsecops-agent", "T-066", "roadmap", "sprint-S6"],
        "body": """Implement `get_sast_results()` per tool registry (**Roadmap**).

**Agent:** DevSecOps | **Method:** Roadmap
**System:** SonarCloud/SonarQube or Semgrep API token
**API:** SonarCloud issues search; Semgrep deployment findings
**Returns:** quality_gate_status, code_smell_count, security_hotspots[], technical_debt_minutes, coverage_pct

**Acceptance criteria:**
- SonarCloud/Semgrep connector config per tenant
- SOC2 compliance evidence export from SAST results""",
    },
    {
        "task": "T-067",
        "summary": "check_compliance_posture() — DevSecOps agent tool (Roadmap)",
        "labels": ["tool-registry", "devsecops-agent", "T-067", "roadmap", "sprint-S6"],
        "body": """Implement `check_compliance_posture()` per tool registry (**Roadmap**).

**Agent:** DevSecOps | **Method:** Roadmap
**System:** AWS Security Hub; optional Wiz/Orca
**API:** `POST securityhub.amazonaws.com → GetFindings` (CRITICAL/HIGH active)
**Returns:** compliance_framework_status, control_failures[], evidence_gaps[], overall_posture_score

**Acceptance criteria:**
- Security Hub connector with framework mapping (SOC2/ISO27001/PCI)
- One-page compliance posture summary for enterprise customers""",
    },
    {
        "task": "T-068",
        "summary": "MCP Phase 3 — DevOps github-mcp tool wrappers",
        "labels": ["tool-registry", "devops-agent", "mcp-phase-3", "T-068", "sprint-S5"],
        "body": """Expose DevOps API+MCP tools via github-mcp server (Phase 3).

**Tools:** get_ci_status, get_deploy_history, check_branch_protection, get_pr_status
**MCP mappings:** list_workflow_runs, list_deployments, get_branch_protection_rules, list_pull_requests

**Acceptance criteria:**
- MCP server config documented for tenants
- LLM agent can invoke tools via MCP when broker configured
- Fallback to direct API when MCP unavailable""",
    },
    {
        "task": "T-069",
        "summary": "MCP Phase 3 — PM atlassian-mcp tool wrappers",
        "labels": ["tool-registry", "pm-agent", "mcp-phase-3", "T-069", "sprint-S5"],
        "body": """Expose PM API+MCP tools via atlassian-mcp server (Phase 3).

**Tools:** get_sprint_status, count_blockers, get_open_defects
**MCP mappings:** get_active_sprint, list_sprint_issues, search_issues (JQL)

**Acceptance criteria:**
- MCP wrappers return same ToolResult schema as direct API
- JQL templates match registry spec""",
    },
    {
        "task": "T-070",
        "summary": "MCP Phase 3 — DevSecOps github-mcp security wrappers",
        "labels": ["tool-registry", "devsecops-agent", "mcp-phase-3", "T-070", "sprint-S5"],
        "body": """Expose DevSecOps API+MCP tools via github-mcp (Phase 3).

**Tools:** scan_cves, scan_secrets
**MCP mappings:** list_code_scanning_alerts, list_secret_scanning_alerts

**Acceptance criteria:**
- Critical CVE and open-secret hard-block paths preserved via MCP
- Same confidence override rules (0.92 CVE, 0.98 secret)""",
    },
    {
        "task": "T-071",
        "summary": "Tool registry contract tests — all 28 agent tools",
        "labels": ["tool-registry", "T-071", "sprint-S4"],
        "body": """Add contract tests validating all 28 tools in `tool_registry_full.html`.

**Shipped (17):** get_ci_status, get_deploy_history, detect_rollbacks, check_branch_protection, get_sprint_status, count_blockers, get_open_defects, calc_velocity_risk, get_spend_trend, check_budget_pace, detect_scaling_anomaly, calc_unit_cost, check_ri_coverage, scan_cves, scan_secrets, check_policy_violations, audit_dependencies

**Pending:** T-057–T-067

**Acceptance criteria:**
- `tests/test_tool_registry_contract.py` asserts required raw_signals keys per tool
- CI runs contract suite in sim_mode
- Registry doc linked from README or docs/""",
    },
]

SHIPPED_STORIES: list[dict] = [
    {
        "task": "T-072",
        "summary": "DevOps shipped tools — registry contract verification",
        "labels": ["tool-registry", "devops-agent", "T-072", "shipped", "sprint-S3"],
        "body": "Verify get_ci_status, get_deploy_history, detect_rollbacks, check_branch_protection match registry.",
    },
    {
        "task": "T-073",
        "summary": "PM shipped tools — registry contract verification",
        "labels": ["tool-registry", "pm-agent", "T-073", "shipped", "sprint-S3"],
        "body": "Verify get_sprint_status, count_blockers, get_open_defects, calc_velocity_risk match registry.",
    },
    {
        "task": "T-074",
        "summary": "FinOps shipped tools — registry contract verification",
        "labels": ["tool-registry", "finops-agent", "T-074", "shipped", "sprint-S3"],
        "body": "Verify get_spend_trend, check_budget_pace, detect_scaling_anomaly, calc_unit_cost, check_ri_coverage match registry.",
    },
    {
        "task": "T-075",
        "summary": "DevSecOps shipped tools — registry contract verification",
        "labels": ["tool-registry", "devsecops-agent", "T-075", "shipped", "sprint-S3"],
        "body": "Verify scan_cves, scan_secrets, check_policy_violations, audit_dependencies match registry.",
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


def create_story(auth: str, *, task: str, summary: str, body: str, labels: list[str]) -> str:
    payload = {
        "fields": {
            "project": {"key": "CAS"},
            "issuetype": {"name": "Story"},
            "summary": f"{task}: {summary}",
            "description": body,
            "parent": {"key": EPIC_KEY},
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

    import base64

    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    created: list[str] = []

    for story in STORIES:
        key = create_story(
            auth,
            task=story["task"],
            summary=story["summary"],
            body=story["body"],
            labels=story["labels"],
        )
        created.append(key)
        print(f"Created {key}: {story['task']} {story['summary']}")

    for story in SHIPPED_STORIES:
        key = create_story(
            auth,
            task=story["task"],
            summary=story["summary"],
            body=story["body"],
            labels=story["labels"],
        )
        created.append(key)
        print(f"Created {key}: {story['task']} {story['summary']}")

    print(f"\nDone — {len(created)} stories under {EPIC_KEY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
