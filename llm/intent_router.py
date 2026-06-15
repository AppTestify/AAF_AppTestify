"""LLM intent router for Phase 3 governance — semantic PM prompt classification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aaf.config import Settings
from app.services.llm_runtime import ActiveProvider, invoke_json_with_failover
from guardrails.llm_cost_tracker import LlmCostTracker
from pm_interface.intent_classifier import IntentCategory, IntentResult, classify_pm_intent

_INTENT_VALUES = frozenset(
    {"release_readiness", "reliability", "cost", "security", "cross_domain"}
)
_AGENT_ALIASES = {
    "pm": "project_management",
    "project_management": "project_management",
    "devops": "devops",
    "finops": "finops",
    "devsecops": "devsecops",
    "secops": "devsecops",
}
_DEFAULT_AGENTS_BY_INTENT: dict[str, list[str]] = {
    "release_readiness": ["devops", "project_management", "finops"],
    "reliability": ["devops", "project_management", "finops"],
    "cost": ["project_management", "finops"],
    "security": ["devops", "project_management", "finops", "devsecops"],
    "cross_domain": ["devops", "project_management", "finops", "devsecops"],
}
_CONNECTORS_BY_INTENT: dict[str, list[str]] = {
    "release_readiness": ["github", "jira", "finops"],
    "reliability": ["github", "jira", "pagerduty"],
    "cost": ["finops", "jira", "github"],
    "security": ["github", "jira", "finops"],
    "cross_domain": ["github", "jira", "finops"],
}
_INTENT_TO_CATEGORY = {
    "release_readiness": IntentCategory.RELEASE_READINESS,
    "reliability": IntentCategory.RELEASE_READINESS,
    "cost": IntentCategory.COST_ANOMALY,
    "security": IntentCategory.SECURITY_GATE,
    "cross_domain": IntentCategory.CROSS_DOMAIN,
}

_SYSTEM_PROMPT = (
    "Classify this PM governance question into one of: "
    "release_readiness | reliability | cost | security | cross_domain. "
    "Return JSON only: "
    '{"intent": "<category>", "agents_needed": ["devops","pm","finops"], "reasoning": "<one sentence>"}. '
    "Use agent ids devops, pm, finops, devsecops as needed."
)


@dataclass(frozen=True)
class IntentRouterResult:
    intent: str
    agents_needed: list[str]
    connectors: list[str]
    reasoning: str
    confidence: float
    source: str
    category: IntentCategory

    def to_intent_payload(self, *, pipeline_phase: int) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "intent": self.intent,
            "agents_needed": self.agents_needed,
            "connectors": self.connectors,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "source": self.source,
            "pipeline_phase": pipeline_phase,
        }


def _normalize_agents(raw: Any, intent: str) -> list[str]:
    if not isinstance(raw, list):
        return list(_DEFAULT_AGENTS_BY_INTENT.get(intent, _DEFAULT_AGENTS_BY_INTENT["release_readiness"]))
    out: list[str] = []
    for item in raw:
        key = str(item or "").strip().lower()
        if not key:
            continue
        mapped = _AGENT_ALIASES.get(key, key)
        if mapped not in out:
            out.append(mapped)
    return out or list(_DEFAULT_AGENTS_BY_INTENT.get(intent, _DEFAULT_AGENTS_BY_INTENT["release_readiness"]))


def _from_keyword_fallback(prompt: str) -> IntentRouterResult:
    keyword = classify_pm_intent(prompt)
    return IntentRouterResult(
        intent=keyword.intent.value,
        agents_needed=list(keyword.agents_needed),
        connectors=list(keyword.connectors),
        reasoning="Keyword classifier fallback (no LLM provider or router failure).",
        confidence=keyword.confidence,
        source="keyword_classifier",
        category=keyword.intent,
    )


def _from_llm_json(prompt: str, payload: dict[str, Any]) -> IntentRouterResult:
    intent = str(payload.get("intent") or "release_readiness").strip().lower()
    if intent not in _INTENT_VALUES:
        intent = "cross_domain"
    agents = _normalize_agents(payload.get("agents_needed"), intent)
    reasoning = str(payload.get("reasoning") or "").strip() or "LLM intent router classification."
    return IntentRouterResult(
        intent=intent,
        agents_needed=agents,
        connectors=list(_CONNECTORS_BY_INTENT.get(intent, ["github", "jira", "finops"])),
        reasoning=reasoning,
        confidence=0.82,
        source="llm_intent_router",
        category=_INTENT_TO_CATEGORY.get(intent, IntentCategory.CROSS_DOMAIN),
    )


def route_pm_intent(
    prompt: str,
    *,
    settings: Settings,
    llm_providers: list[ActiveProvider] | None = None,
    cost_tracker: LlmCostTracker | None = None,
) -> IntentRouterResult:
    """Route PM prompt via LLM when Phase 3 is enabled; otherwise keyword classifier."""
    if settings.pipeline_phase < 3 or not llm_providers:
        return _from_keyword_fallback(prompt)

    tracker = cost_tracker or LlmCostTracker()
    if len(tracker.calls) >= settings.max_llm_calls_per_run:
        fallback = _from_keyword_fallback(prompt)
        return IntentRouterResult(
            intent=fallback.intent,
            agents_needed=fallback.agents_needed,
            connectors=fallback.connectors,
            reasoning="LLM call budget exhausted before intent routing.",
            confidence=fallback.confidence,
            source="keyword_classifier",
            category=fallback.category,
        )

    user_prompt = f"PM governance question:\n{prompt}"
    try:
        payload, meta = invoke_json_with_failover(llm_providers, user_prompt, system_prompt=_SYSTEM_PROMPT)
        tracker.record_from_meta(
            phase="intent_router",
            agent_id="orchestrator",
            meta=meta,
            prompt_text=_SYSTEM_PROMPT + user_prompt,
            completion_text=str(payload),
        )
        return _from_llm_json(prompt, payload)
    except Exception:
        return _from_keyword_fallback(prompt)


def intent_result_from_router(router: IntentRouterResult) -> IntentResult:
    """Bridge to Phase 1 IntentResult for legacy callers."""
    return IntentResult(
        intent=router.category,
        agents_needed=list(router.agents_needed),
        connectors=list(router.connectors),
        confidence=router.confidence,
    )
