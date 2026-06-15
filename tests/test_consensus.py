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


def test_consensus_phase1_payments_release():
    from orchestrator.consensus import compute_consensus_phase1
    opinions = [
        AgentOpinion(
            agent_id="devops",
            claim="Payments release looks solid",
            confidence=0.52, # mean will be exactly 0.52 if all are 0.52
            risk_theme=RiskTheme.OPERATIONAL_RISK,
        ),
        AgentOpinion(
            agent_id="finops",
            claim="Payments release within budget",
            confidence=0.52,
            risk_theme=RiskTheme.COST_RISK, # compatible with operational
        ),
        AgentOpinion(
            agent_id="pm",
            claim="Payments sprint complete",
            confidence=0.52,
            risk_theme=RiskTheme.DELIVERY_RISK, # compatible with operational
        ),
    ]
    # pairs: (op, cost) -> compat
    #        (op, delivery) -> compat
    #        (cost, delivery) -> conflict
    # conflict_pairs = 1, total_pairs = 3. ratio = 0.333, agreement = 0.666
    # mean_conf = 0.52. C = 0.5 * 0.52 + 0.5 * 0.666 = 0.26 + 0.333 = 0.593
    c = compute_consensus_phase1(opinions)
    assert 0.59 <= c.consensus_score <= 0.60

