from __future__ import annotations

import pytest

from aaf.config import Settings
from aaf.schema import AgentOpinion, EvidenceRecord, GovernanceAction, RiskTheme
from orchestrator.evidence import collect_evidence
from orchestrator.utility import score_actions
from tools.context import build_tool_context, get_cached_tool_result


@pytest.mark.asyncio
async def test_collect_evidence_builds_package():
    settings = Settings()
    raw, normalized, package, tool_ctx = await collect_evidence(
        settings=settings,
        prompt="Should we release?",
        connector_names=["github", "jira", "finops"],
        ctx={"prompt": "Should we release?", "github_repo": settings.github_repo, "jira_project": settings.jira_project},
        warm_tools=True,
    )
    assert raw
    assert normalized
    assert package["prompt"] == "Should we release?"
    assert tool_ctx.evidence_package is not None
    assert "tools" in tool_ctx.evidence_package


def test_package_backed_ci_status_cache():
    settings = Settings()
    ctx = build_tool_context(
        settings,
        evidence_package={
            "tools": {
                "get_ci_status": {
                    "tool_name": "get_ci_status",
                    "signal": 0.8,
                    "captured_at": "2026-06-12T12:00:00+00:00",
                    "raw_signals": {"ci_pass_rate": 0.2},
                    "evidence_lines": ["CI pass rate (24h): 20.0%"],
                }
            }
        },
    )
    cached = get_cached_tool_result(ctx, "get_ci_status")
    assert cached is not None
    assert cached.raw_signals["ci_pass_rate"] == 0.2


def test_hold_release_scoring():
    settings = Settings()
    opinions = [
        AgentOpinion(agent_id="devops", claim="CI failing", confidence=0.7, risk_theme=RiskTheme.OPERATIONAL_RISK),
        AgentOpinion(agent_id="finops", claim="Spend spike", confidence=0.45, risk_theme=RiskTheme.COST_RISK),
        AgentOpinion(
            agent_id="devsecops",
            claim="Policy gaps",
            confidence=0.1,
            risk_theme=RiskTheme.SECURITY_RISK,
        ),
    ]
    evidence = [
        EvidenceRecord(source="github", kind="workflow_run", summary="CI failed", severity=0.9),
        EvidenceRecord(source="finops", kind="cost_anomaly", summary="Spike", severity=0.8),
    ]
    utility = score_actions(evidence, settings, opinions=opinions)
    assert GovernanceAction.HOLD_RELEASE.value in utility.scores_by_action
