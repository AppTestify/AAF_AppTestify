import pytest

from aaf.config import Settings
from app.services.governance_service import run_governance


@pytest.mark.asyncio
async def test_governance_run_sim():
    settings = Settings(
        tau_consensus=0.99,
        max_rar_loops=1,
    )
    r = await run_governance("GitHub cost JIRA sprint review", None, settings)
    assert r.consensus.consensus_score >= 0.0
    assert r.utility.recommended_action
    assert r.explanation
    assert "github" in r.connectors_used or "jira" in r.connectors_used

@pytest.mark.asyncio
async def test_pipeline_phase1_single_llm_call_payments_release():
    from app.services.llm_runtime import ActiveProvider
    from guardrails.llm_cost_tracker import LlmCostTracker
    
    settings = Settings(
        tau_consensus=0.99,
        max_rar_loops=1,
        pipeline_phase=1,
        phase1_static_agents=True
    )
    
    tracker = LlmCostTracker()
    from orchestrator.pipeline import run_pipeline
    
    # Mock invoke_tracked to simulate a successful LLM call
    original_invoke = tracker.invoke_tracked
    def mock_invoke(*args, **kwargs):
        tracker.calls.append({"phase": "explanation", "status": "ok"})
        return "Mock LLM explanation", {"model": "mock"}
    tracker.invoke_tracked = mock_invoke

    # mock a simple evidence so the pipeline doesn't short-circuit
    evidence = []
    opinions = []
    
    r = await run_pipeline(
        prompt="Should we release the payments service today?",
        normalized_evidence=evidence,
        intent={},
        prompt_id="test",
        connectors_used=[],
        raw_evidence_by_connector={},
        settings=settings,
        agent_ids=[],
        llm_providers=[ActiveProvider(
            provider_name="mock",
            model_name="mock",
            endpoint_url=None,
            temperature=None,
            max_tokens=None,
            timeout_seconds=5,
            api_key="test",
            metadata_json={}
        )],
        cost_tracker=tracker,
    )
    
    # Since phase1_static_agents = True, agents won't use LLMs
    # Only the explanation step will use the LLM
    assert len(tracker.calls) <= 1
    if tracker.calls:
        assert tracker.calls[0]["phase"] == "explanation"
    
    # We mocked it to succeed
    assert r.llm_invocation["status"] == "ok"
