from __future__ import annotations

from unittest.mock import patch

from aaf.config import Settings
from llm.intent_router import route_pm_intent
from pm_interface.intent_classifier import classify_pm_intent


def test_keyword_fallback_when_phase_one():
    settings = Settings(pipeline_phase=1)
    result = route_pm_intent("Should we release today?", settings=settings, llm_providers=[])
    keyword = classify_pm_intent("Should we release today?")
    assert result.source == "keyword_classifier"
    assert result.agents_needed == keyword.agents_needed
    assert result.category == keyword.intent


def test_keyword_fallback_without_providers_on_phase_three():
    settings = Settings(pipeline_phase=3)
    result = route_pm_intent("Are we good for Monday?", settings=settings, llm_providers=[])
    assert result.source == "keyword_classifier"
    assert result.agents_needed


@patch("llm.intent_router.invoke_json_with_failover")
def test_llm_router_parses_json(mock_invoke):
    mock_invoke.return_value = (
        {
            "intent": "release_readiness",
            "agents_needed": ["devops", "pm", "finops"],
            "reasoning": "Release decision query.",
        },
        {"provider": "openai", "model": "gpt-4o-mini", "prompt_tokens": 10, "completion_tokens": 20},
    )
    settings = Settings(pipeline_phase=3)
    provider = object()
    result = route_pm_intent(
        "Can we go?",
        settings=settings,
        llm_providers=[provider],  # type: ignore[list-item]
    )
    assert result.source == "llm_intent_router"
    assert result.intent == "release_readiness"
    assert "devops" in result.agents_needed
    assert "project_management" in result.agents_needed
    assert result.reasoning == "Release decision query."


@patch("llm.intent_router.invoke_json_with_failover")
def test_llm_router_falls_back_on_failure(mock_invoke):
    mock_invoke.side_effect = RuntimeError("provider down")
    settings = Settings(pipeline_phase=3)
    result = route_pm_intent(
        "Can we go?",
        settings=settings,
        llm_providers=[object()],  # type: ignore[list-item]
    )
    assert result.source == "keyword_classifier"
