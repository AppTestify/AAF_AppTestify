from __future__ import annotations

from aaf.schema import AgentOpinion, RiskTheme
from guardrails.agent_output_guard import check_agent_opinion, guard_agent_opinions


def test_passes_valid_opinion():
    opinion = AgentOpinion(
        agent_id="devops",
        claim="CI failures detected on main branch.",
        confidence=0.8,
        risk_theme=RiskTheme.OPERATIONAL_RISK,
    )
    result = check_agent_opinion(opinion)
    assert result.passed
    assert result.sanitized_agent_opinion is not None
    assert result.sanitized_agent_opinion.claim == opinion.claim


def test_degrades_empty_claim():
    opinion = AgentOpinion(
        agent_id="finops",
        claim="   ",
        confidence=0.5,
        risk_theme=RiskTheme.COST_RISK,
    )
    result = check_agent_opinion(opinion)
    assert not result.passed
    assert result.sanitized_agent_opinion is not None
    assert "degraded" in (result.sanitized_agent_opinion.raw_signals or {})


def test_degrades_high_confidence_unknown_theme():
    opinion = AgentOpinion(
        agent_id="devsecops",
        claim="Possible vulnerability exposure.",
        confidence=0.9,
        risk_theme=RiskTheme.UNKNOWN,
    )
    result = check_agent_opinion(opinion)
    assert not result.passed
    assert result.sanitized_agent_opinion is not None
    assert result.sanitized_agent_opinion.confidence == 0.3


def test_guard_agent_opinions_batch():
    opinions = [
        AgentOpinion(agent_id="devops", claim="ok", confidence=0.6, risk_theme=RiskTheme.OPERATIONAL_RISK),
        AgentOpinion(agent_id="finops", claim="", confidence=0.5, risk_theme=RiskTheme.COST_RISK),
    ]
    guarded, reports = guard_agent_opinions(opinions)
    assert len(guarded) == 2
    assert len(reports) == 2
    assert reports[0].passed
    assert not reports[1].passed
