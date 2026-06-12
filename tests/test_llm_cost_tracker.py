from __future__ import annotations

from guardrails.llm_cost_tracker import LlmCostTracker, estimate_cost_usd, estimate_tokens


def test_estimate_tokens_from_text():
    assert estimate_tokens("abcd") >= 1
    assert estimate_tokens("") == 0


def test_estimate_cost_known_model():
    cost = estimate_cost_usd("gpt-4o-mini", prompt_tokens=1000, completion_tokens=500)
    assert cost > 0


def test_tracker_snapshot_totals():
    tracker = LlmCostTracker()
    tracker.record_from_meta(
        phase="explanation",
        agent_id="orchestrator",
        meta={"provider": "openai", "model": "gpt-4o-mini", "prompt_tokens": 100, "completion_tokens": 50},
        prompt_text="hello",
        completion_text="world",
    )
    snap = tracker.snapshot()
    assert snap["totals"]["call_count"] == 1
    assert snap["totals"]["prompt_tokens"] == 100
    assert snap["by_phase"]["explanation"] > 0
