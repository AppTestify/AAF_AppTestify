#!/usr/bin/env python3
"""Create Jira epic + stories for Phase 3 LLM Agentic Governance Pipeline (T-162–T-179)."""

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

EPIC_KEY = "CAS-183"  # created 2026-06-12 via MCP (CAS-164 is T-143 story); use --stories-only
EPIC_SUMMARY = "Phase 3 LLM Agentic Governance Pipeline"
EPIC_BODY = """LLM-powered agentic governance pipeline per phase-3-governance-flow.md.

**Goals:**
- LLM intent router (semantic agent selection)
- Evidence package-backed tool execution
- Selective ReAct loops with 7–9 LLM call budget
- HOLD_RELEASE governance action
- CAS-115 Phase 3 decision flow UI
- Live MCP/connector production validation

**Related:** CAS-71 (tool registry), CAS-115 (Phase 3 UI), CAS-100 (Phase 1 flow)

**Sprints:** P1–P6 on board 134"""

STORIES: list[dict] = [
    {
        "task": "T-162",
        "summary": "llm/intent_router.py — semantic intent classification",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P1"],
        "body": """LLM intent router for semantic PM question classification.

**Acceptance criteria:**
- New llm/intent_router.py returns JSON { intent, agents_needed[], reasoning }
- Intents: release_readiness | reliability | cost | security | cross_domain

**Files:** llm/intent_router.py""",
    },
    {
        "task": "T-163",
        "summary": "Wire intent router into pipeline",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P1"],
        "body": """Integrate LLM intent router into governance pipeline.

**Acceptance criteria:**
- governance_service.py and orchestrator/pipeline.py use intent router when pipeline_phase=3
- Tenant setting pipeline_phase: 1|3

**Files:** app/services/governance_service.py, orchestrator/pipeline.py""",
    },
    {
        "task": "T-164",
        "summary": "Intent router fallback + tests",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P1"],
        "body": """Fallback and test coverage for intent router.

**Acceptance criteria:**
- Fallback to classify_pm_intent on LLM failure
- tests/test_intent_router.py with mocked LLM responses

**Files:** llm/intent_router.py, pm_interface/intent_classifier.py, tests/test_intent_router.py""",
    },
    {
        "task": "T-165",
        "summary": "Evidence package builder at collect_evidence",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P2"],
        "body": """Pre-fetch connector signals into EvidencePackage.

**Acceptance criteria:**
- collect_evidence builds ~45 signals per phase-3 spec
- EvidencePackage passed to all LLM agents before tool loops

**Files:** agents/schemas.py, orchestrator/pipeline.py""",
    },
    {
        "task": "T-166",
        "summary": "Package-backed tool execution",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P2"],
        "body": """Tools read pre-fetched evidence package first.

**Acceptance criteria:**
- ToolContext carries evidence_package
- Tools read package first; skip live API when signal present
- Phase 3 run with connectors disabled still returns tool results

**Files:** tools/context.py, tools/""",
    },
    {
        "task": "T-167",
        "summary": "Selective live refresh via refresh_tools",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P2"],
        "body": """RAR loop can refresh specific tools live.

**Acceptance criteria:**
- refresh_tools parameter for selective live API refresh
- Package staleness metadata in raw_signals

**Files:** agents/llm_tool_loop.py, tools/context.py""",
    },
    {
        "task": "T-168",
        "summary": "Complete selective ReAct loop",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P3"],
        "body": """Record tool call telemetry in agent opinions.

**Acceptance criteria:**
- llm_tool_loop.py records tools_called[], tools_skipped[] in AgentOpinion.raw_signals
- Selective invocation: 6 of 21 tools typical per run

**Files:** agents/llm_tool_loop.py""",
    },
    {
        "task": "T-169",
        "summary": "Per-run LLM call counter in PipelineResult",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P3"],
        "body": """Expose LLM invocation metrics in run JSON.

**Acceptance criteria:**
- Extend LlmCostTracker; expose llm_invocation block in PipelineResult
- Count intent + agent + explain calls

**Files:** guardrails/llm_cost_tracker.py, orchestrator/pipeline.py""",
    },
    {
        "task": "T-170",
        "summary": "7–9 LLM call budget cap",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P3"],
        "body": """Enforce per-run LLM call budget.

**Acceptance criteria:**
- Settings max_llm_calls_per_run (default 9)
- Block/warn when exceeded: intent(1) + agents(4–6) + explain(1)

**Files:** app/settings.py, guardrails/llm_cost_tracker.py""",
    },
    {
        "task": "T-171",
        "summary": "Add HOLD_RELEASE to GovernanceAction",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P4"],
        "body": """New governance action for release holds.

**Acceptance criteria:**
- HOLD_RELEASE in aaf/schema.py GovernanceAction enum
- API types and migration if persisted

**Files:** aaf/schema.py""",
    },
    {
        "task": "T-172",
        "summary": "Utility scoring for HOLD_RELEASE",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P4"],
        "body": """Orchestrator utility scoring for hold decisions.

**Acceptance criteria:**
- orchestrator/utility.py higher weight on delivery + reliability risk
- HOLD_RELEASE can win over MITIGATE_AND_MONITOR when signals warrant

**Files:** orchestrator/utility.py""",
    },
    {
        "task": "T-173",
        "summary": "Guards + explainer support",
        "labels": ["phase-3", "governance-pipeline", "llm", "sprint-P4"],
        "body": """Brief guard and explainer support for HOLD_RELEASE.

**Acceptance criteria:**
- brief_output_guard.py allows HOLD_RELEASE language
- deterministic_explainer.py keywords for hold scenarios

**Files:** guardrails/brief_output_guard.py, llm/deterministic_explainer.py""",
    },
    {
        "task": "T-174",
        "summary": "Phase 3 flow stepper — intent router step",
        "labels": ["phase-3", "governance-pipeline", "llm", "frontend", "sprint-P5", "CAS-115"],
        "body": """Update decision flow for Phase 3 pipeline visualization.

**Acceptance criteria:**
- governancePresentation.ts deriveDecisionFlow adds LLM Intent Router step when pipeline_phase=3
- Step sequence: PM Prompt → Intent Router → Evidence → Agents → Orchestrator → Explanation → Brief
- Links to CAS-115

**Files:** frontend/src/lib/governancePresentation.ts""",
    },
    {
        "task": "T-175",
        "summary": "Per-agent tool-call counts in UI",
        "labels": ["phase-3", "governance-pipeline", "llm", "frontend", "sprint-P5", "CAS-115"],
        "body": """Show tool invocation counts in governance UI.

**Acceptance criteria:**
- AgentReasoningGrid shows "DevOps 2/7 tools" from raw_signals
- GovernanceFlowStepper updates if needed
- Links to CAS-115

**Files:** frontend/src/components/governance/AgentReasoningGrid.tsx, GovernanceFlowStepper.tsx""",
    },
    {
        "task": "T-176",
        "summary": "HOLD_RELEASE distinct styling",
        "labels": ["phase-3", "governance-pipeline", "llm", "frontend", "sprint-P5", "CAS-115"],
        "body": """Distinct UI styling for HOLD_RELEASE action.

**Acceptance criteria:**
- ConsensusDecisionPanel + formatActionLabel: hold_release red/amber badge
- Distinct from MITIGATE_AND_MONITOR styling
- Links to CAS-115

**Files:** frontend/src/components/governance/ConsensusDecisionPanel.tsx""",
    },
    {
        "task": "T-177",
        "summary": "MCP production validation runbook",
        "labels": ["phase-3", "governance-pipeline", "llm", "mcp", "sprint-P6"],
        "body": """Production validation runbook for MCP connectors.

**Acceptance criteria:**
- docs/runbooks/mcp-production-validation.md
- Settings checklist in AI Config tab
- Prerequisites: pip install mcp, npx server-github

**Files:** docs/runbooks/mcp-production-validation.md""",
    },
    {
        "task": "T-178",
        "summary": "Live connector E2E script",
        "labels": ["phase-3", "governance-pipeline", "llm", "mcp", "sprint-P6"],
        "body": """E2E validation script for live MCP connectors.

**Acceptance criteria:**
- scripts/validate_mcp_connectors.py
- Tests github-mcp + atlassian-mcp with tenant mcp_servers config

**Files:** scripts/validate_mcp_connectors.py""",
    },
    {
        "task": "T-179",
        "summary": "MCP transport observability in run results",
        "labels": ["phase-3", "governance-pipeline", "llm", "mcp", "sprint-P6"],
        "body": """Surface MCP transport metadata in UI.

**Acceptance criteria:**
- raw_signals.transport: mcp surfaces in Runs UI + Reports
- MCP badge in AgentReasoningGrid or run detail
- Python 3.10+ deployment note in runbook

**Files:** frontend/src/components/governance/AgentReasoningGrid.tsx""",
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
            "labels": ["phase-3", "governance-pipeline", "llm", "mcp"],
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
