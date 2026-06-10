import pytest
from unittest.mock import patch
from aaf.schema import EvidenceRecord, RiskTheme
from app.services.llm_runtime import ActiveProvider
from agents import devops, sre, finops, devsecops, pm_agent


def test_agents_fallback_mode():
    evidence = [
        EvidenceRecord(source="github", kind="workflow_fail", summary="CI workflow failed on main", severity=0.8),
        EvidenceRecord(source="jira", kind="overdue_task", summary="Sprint issue is overdue", severity=0.7),
        EvidenceRecord(source="finops", kind="cost_anomaly", summary="Unusual cost spike detected", severity=0.9),
    ]
    
    op_devops = devops.run(evidence, llm_providers=None)
    assert op_devops.agent_id == "devops"
    assert op_devops.risk_theme == RiskTheme.OPERATIONAL_RISK
    assert "CI/CD" in op_devops.claim
    
    op_sre = sre.run(evidence, llm_providers=None)
    assert op_sre.agent_id == "sre"
    assert op_sre.risk_theme == RiskTheme.RELIABILITY_RISK
    
    op_finops = finops.run(evidence, llm_providers=None)
    assert op_finops.agent_id == "finops"
    assert op_finops.risk_theme == RiskTheme.COST_RISK
    
    op_pm = pm_agent.run(evidence, llm_providers=None)
    assert op_pm.agent_id == "project_management"
    assert op_pm.risk_theme == RiskTheme.DELIVERY_RISK


@patch("agents.base.invoke_json_with_failover")
def test_agents_llm_success(mock_invoke):
    evidence = [
        EvidenceRecord(source="finops", kind="cost_anomaly", summary="Unusual cost spike detected", severity=0.9),
    ]
    
    mock_invoke.return_value = (
        {
            "claim": "LLM Cost Alert",
            "confidence": 0.85,
            "evidence_refs": ["finops:Unusual cost spike detected"],
            "risk_theme": "cost_risk",
            "raw_signals": {"llm_signal": 123}
        },
        {"provider": "openai"}
    )
    
    provider = ActiveProvider(
        provider_name="openai",
        model_name="gpt-4o",
        endpoint_url=None,
        temperature=0.2,
        max_tokens=200,
        timeout_seconds=10,
        api_key="mock-key",
        metadata_json={}
    )
    
    op_finops = finops.run(evidence, llm_providers=[provider])
    assert op_finops.agent_id == "finops"
    assert op_finops.claim == "LLM Cost Alert"
    assert op_finops.confidence == 0.85
    assert op_finops.risk_theme == RiskTheme.COST_RISK
    assert op_finops.raw_signals == {"llm_signal": 123}
    
    mock_invoke.assert_called_once()
    args, kwargs = mock_invoke.call_args
    assert kwargs["system_prompt"] == finops.SYSTEM_PROMPT
    assert "cost_anomaly" in kwargs["prompt"]


@patch("agents.base.invoke_json_with_failover")
def test_agents_llm_failure_fallback(mock_invoke):
    evidence = [
        EvidenceRecord(source="finops", kind="cost_anomaly", summary="Unusual cost spike detected", severity=0.9),
    ]
    
    mock_invoke.side_effect = RuntimeError("API Limit Exceeded")
    
    provider = ActiveProvider(
        provider_name="openai",
        model_name="gpt-4o",
        endpoint_url=None,
        temperature=0.2,
        max_tokens=200,
        timeout_seconds=10,
        api_key="mock-key",
        metadata_json={}
    )
    
    op_finops = finops.run(evidence, llm_providers=[provider])
    assert op_finops.agent_id == "finops"
    assert op_finops.claim == "Cloud spend or budget variance requires attention."
    assert op_finops.risk_theme == RiskTheme.COST_RISK
