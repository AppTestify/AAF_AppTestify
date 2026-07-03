from __future__ import annotations

import pytest
from unittest.mock import patch

from aaf.config import Settings
from aaf.schema import RiskTheme, EvidenceRecord
from agents.pm_agent import PMAgent
from agents.schemas import EvidencePackage
from app.services.llm_runtime import ActiveProvider
from tools.context import build_tool_context


@pytest.mark.asyncio
async def test_pm_llm_loop_selective_invocation():
    settings = Settings(
        max_tool_calls_per_agent=5,
        connector_mode="sim",
    )
    
    agent = PMAgent()
    ctx = build_tool_context(settings)
    ctx.evidence_package = {
        "tools": {},
        "records": []
    }
    
    # Evidence lines mention customer-reported critical bug
    records = [
        EvidenceRecord(
            source="jira",
            kind="incident",
            summary="Customer-reported critical payments bug in production",
            severity=0.9
        )
    ]
    package = EvidencePackage(
        records=records,
        prompt="Assess sprint delivery risk"
    )

    call_count = 0
    def mock_invoke_json(providers, prompt, system_prompt=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "thought": "I should check for blockers first.",
                "tool_name": "count_blockers",
                "done": False
            }, {"model": "mock"}
        elif call_count == 2:
            return {
                "thought": "Found 3 blockers (including a 5-day platform dep). Let's check open defects next.",
                "tool_name": "get_open_defects",
                "done": False
            }, {"model": "mock"}
        else:
            return {
                "thought": "Found 1 critical payments bug from open defects and the customer report. High delivery risk.",
                "done": True,
                "claim": "Delivery risk is elevated due to 3 blockers (5-day platform dep) and 1 customer-reported critical payments bug.",
                "confidence": 0.82,
                "risk_theme": "delivery_risk"
            }, {"model": "mock"}

    mock_providers = [
        ActiveProvider(
            provider_name="mock",
            model_name="mock",
            endpoint_url=None,
            temperature=None,
            max_tokens=None,
            timeout_seconds=5,
            api_key="test",
            metadata_json={}
        )
    ]

    with patch("agents.llm_tool_loop.invoke_json_with_failover", side_effect=mock_invoke_json):
        opinion = await agent.run_llm_loop(
            ctx=ctx,
            package=package,
            llm_providers=mock_providers,
            settings=settings,
        )

    assert opinion.confidence == 0.82
    assert opinion.risk_theme == RiskTheme.DELIVERY_RISK
    assert "critical payments bug" in opinion.claim
    
    raw = opinion.raw_signals
    # Example: 2/7 tools called (note: pm agent actually has 10 tools registered in tool_callables)
    # The requirement says "2/7 tools". Maybe the PM agent has 10 tools now, but the loop just needs to call 2 of them.
    assert raw["tools_called"] == ["count_blockers", "get_open_defects"]
    assert len(raw["tools_called"]) == 2
    
    skipped = raw["skipped_tools"]
    assert "count_blockers" not in skipped
    assert "get_open_defects" not in skipped
    
    # Verify the remaining tools are skipped
    allowlist = [fn.__name__ for fn in agent.tool_callables()]
    expected_skipped_count = len(allowlist) - 2
    assert len(skipped) == expected_skipped_count
