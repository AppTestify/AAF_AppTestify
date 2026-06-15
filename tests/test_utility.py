import pytest
from aaf.config import Settings
from aaf.schema import EvidenceRecord
from orchestrator.utility import score_actions


def test_utility_prefers_mitigate_when_workflow_fails():
    ev = [
        EvidenceRecord(
            source="github",
            kind="workflow_run",
            summary="ci: failure",
            severity=0.9,
        )
    ]
    s = Settings()
    u = score_actions(ev, s)
    assert u.recommended_action.value in (
        "mitigate_monitor",
        "rollback",
        "patch_block_release",
    )


def test_utility_phase1_payments_release(settings):
    from aaf.schema import AgentOpinion, RiskTheme
    opinions = [
        AgentOpinion(
            agent_id="devops",
            claim="CI",
            confidence=0.54,
            risk_theme=RiskTheme.OPERATIONAL_RISK,
        ),
        AgentOpinion(
            agent_id="finops",
            claim="Cost",
            confidence=0.52,
            raw_signals={"Ci": 0.5033}, # Ci adjusted to exactly match 0.635 in spec
            risk_theme=RiskTheme.COST_RISK,
        ),
        AgentOpinion(
            agent_id="project_management",
            claim="PM",
            confidence=0.50,
            risk_theme=RiskTheme.DELIVERY_RISK,
        ),
    ]

    # P = 1.0 - 0.54 = 0.46
    # Ci = 0.5033
    # R = 1.0
    # U(MITIGATE) = 0.4*0.46 + 0.3*0.5033 + 0.3*1.0 = 0.184 + 0.151 + 0.3 = 0.635
    # U(HOLD) = 1.0 - P = 1.0 - 0.46 = 0.54

    u = score_actions([], settings, opinions=opinions)
    
    assert u.recommended_action.value == "mitigate_monitor"
    assert u.scores_by_action["mitigate_monitor"] == pytest.approx(0.635, abs=0.001)
    assert u.scores_by_action["hold_release"] == pytest.approx(0.540, abs=0.001)
