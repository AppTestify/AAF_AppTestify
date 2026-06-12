"""LLM cost tracking — tokens, per-call, per-run totals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.llm_runtime import ActiveProvider, invoke_text_with_failover

# USD per 1K tokens (input, output) — conservative defaults for FinOps estimates
_MODEL_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.005, 0.015),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4-turbo": (0.01, 0.03),
    "gpt-3.5-turbo": (0.0005, 0.0015),
    "claude-3-5-sonnet-20241022": (0.003, 0.015),
    "claude-3-5-haiku-20241022": (0.0008, 0.004),
    "claude-3-opus-20240229": (0.015, 0.075),
}
_DEFAULT_PRICING = (0.002, 0.008)


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_cost_usd(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    key = model_name.lower()
    pricing = _DEFAULT_PRICING
    for model_key, rates in _MODEL_PRICING.items():
        if model_key in key:
            pricing = rates
            break
    in_cost = (prompt_tokens / 1000.0) * pricing[0]
    out_cost = (completion_tokens / 1000.0) * pricing[1]
    return round(in_cost + out_cost, 6)


@dataclass
class LlmCallRecord:
    phase: str
    agent_id: str
    provider_name: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
    status: str = "ok"


@dataclass
class LlmCostTracker:
    calls: list[LlmCallRecord] = field(default_factory=list)

    def record_from_meta(
        self,
        *,
        phase: str,
        agent_id: str,
        meta: dict[str, Any],
        prompt_text: str,
        completion_text: str,
    ) -> LlmCallRecord:
        prompt_tokens = int(meta.get("prompt_tokens") or estimate_tokens(prompt_text))
        completion_tokens = int(meta.get("completion_tokens") or estimate_tokens(completion_text))
        model_name = str(meta.get("model") or "unknown")
        cost_usd = estimate_cost_usd(model_name, prompt_tokens, completion_tokens)
        row = LlmCallRecord(
            phase=phase,
            agent_id=agent_id,
            provider_name=str(meta.get("provider") or "unknown"),
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            latency_ms=int(meta.get("latency_ms") or 0),
            status=str(meta.get("status") or "ok"),
        )
        self.calls.append(row)
        return row

    def invoke_tracked(
        self,
        providers: list[ActiveProvider],
        prompt: str,
        *,
        phase: str,
        agent_id: str,
        system_prompt: Optional[str] = None,
    ) -> tuple[str, dict[str, Any]]:
        text, meta = invoke_text_with_failover(providers, prompt, system_prompt=system_prompt)
        self.record_from_meta(
            phase=phase,
            agent_id=agent_id,
            meta=meta,
            prompt_text=(system_prompt or "") + prompt,
            completion_text=text,
        )
        return text, meta

    def snapshot(self) -> dict[str, Any]:
        total_prompt = sum(c.prompt_tokens for c in self.calls)
        total_completion = sum(c.completion_tokens for c in self.calls)
        total_cost = round(sum(c.cost_usd for c in self.calls), 6)
        by_phase: dict[str, float] = {}
        by_agent: dict[str, float] = {}
        for call in self.calls:
            by_phase[call.phase] = round(by_phase.get(call.phase, 0.0) + call.cost_usd, 6)
            by_agent[call.agent_id] = round(by_agent.get(call.agent_id, 0.0) + call.cost_usd, 6)
        return {
            "calls": [
                {
                    "phase": c.phase,
                    "agent_id": c.agent_id,
                    "provider_name": c.provider_name,
                    "model_name": c.model_name,
                    "prompt_tokens": c.prompt_tokens,
                    "completion_tokens": c.completion_tokens,
                    "cost_usd": c.cost_usd,
                    "latency_ms": c.latency_ms,
                    "status": c.status,
                }
                for c in self.calls
            ],
            "totals": {
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "cost_usd": total_cost,
                "call_count": len(self.calls),
            },
            "by_phase": by_phase,
            "by_agent": by_agent,
        }
