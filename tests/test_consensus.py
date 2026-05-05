from aaf.schema import AgentOpinion, RiskTheme
from orchestrator.consensus import compute_consensus


def test_consensus_agreement():
    opinions = [
        AgentOpinion(
            agent_id="a1",
            claim="x",
            confidence=0.8,
            risk_theme=RiskTheme.OPERATIONAL_RISK,
        ),
        AgentOpinion(
            agent_id="a2",
            claim="y",
            confidence=0.7,
            risk_theme=RiskTheme.RELIABILITY_RISK,
        ),
    ]
    c = compute_consensus(opinions)
    assert 0.0 <= c.consensus_score <= 1.0


def test_consensus_conflict():
    opinions = [
        AgentOpinion(
            agent_id="a1",
            claim="x",
            confidence=0.9,
            risk_theme=RiskTheme.COST_RISK,
        ),
        AgentOpinion(
            agent_id="a2",
            claim="y",
            confidence=0.9,
            risk_theme=RiskTheme.SECURITY_RISK,
        ),
    ]
    c = compute_consensus(opinions)
    assert c.consensus_score < 0.95
