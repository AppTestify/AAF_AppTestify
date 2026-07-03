"""BaseAgent — parallel tool dispatch, weighted confidence, evidence packaging."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.schemas import EvidencePackage, ToolResult
from tools.context import ToolContext
from tools.scoring import ConfidenceScorer

ToolCallable = Callable[[ToolContext], Awaitable[ToolResult]]


class BaseAgent(ABC):
    agent_id: str
    risk_theme_default: RiskTheme = RiskTheme.UNKNOWN
    staleness_hours: float = 4.0
    staleness_penalty: float = 0.5
    min_confidence_floor: float | None = None

    @abstractmethod
    def tool_weights(self) -> dict[str, float]:
        ...

    @abstractmethod
    def tool_callables(self) -> list[ToolCallable]:
        ...

    @abstractmethod
    def generate_claim(self, tool_results: list[ToolResult], package: EvidencePackage) -> str:
        ...

    def determine_risk_theme(self, tool_results: list[ToolResult], confidence: float) -> RiskTheme:
        if confidence < 0.35:
            return RiskTheme.LOW_RISK
        return self.risk_theme_default

    def package_evidence(self, tool_results: list[ToolResult], *, max_lines: int = 6) -> list[str]:
        ranked = sorted(tool_results, key=lambda r: r.signal, reverse=True)
        lines: list[str] = []
        for result in ranked:
            for line in result.evidence_lines:
                if line not in lines:
                    lines.append(line)
                if len(lines) >= max_lines:
                    return lines
        return lines

    def merge_raw_signals(self, tool_results: list[ToolResult]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for result in tool_results:
            merged[result.tool_name] = result.raw_signals
        return merged

    def apply_confidence_rules(self, confidence: float, tool_results: list[ToolResult]) -> float:
        if self.min_confidence_floor is not None:
            confidence = max(confidence, self.min_confidence_floor)
        return confidence

    def correlation_boost(self, tool_results: list[ToolResult]) -> float:
        return 0.0

    async def run_tools(self, ctx: ToolContext, *, refresh_tools: list[str] | None = None) -> list[ToolResult]:
        from aaf.config import get_settings
        from guardrails.tool_scope_guard import filter_allowed_tools
        import dataclasses

        callables = self.tool_callables()
        if refresh_tools:
            name_set = set(refresh_tools)
            callables = [c for c in callables if c.__name__ in name_set]
        if not callables:
            callables = self.tool_callables()

        settings = get_settings()
        tool_names = [fn.__name__ for fn in callables]
        allowed_names, scope_report = filter_allowed_tools(self.agent_id, tool_names, settings)
        if scope_report.blocked:
            raise RuntimeError(
                f"tool_scope_guard blocked agent {self.agent_id}: "
                + "; ".join(v.message for v in scope_report.violations)
            )
        callables = [fn for fn in callables if fn.__name__ in allowed_names]

        if refresh_tools:
            ctx = dataclasses.replace(ctx, extra={**ctx.extra, "refresh_tools": set(refresh_tools)})
        else:
            ctx = dataclasses.replace(ctx, extra={k: v for k, v in ctx.extra.items() if k != "refresh_tools"})

        return list(await asyncio.gather(*[fn(ctx) for fn in callables]))

    def system_prompt(self) -> str:
        return f"You are the {self.agent_id} governance agent."

    async def run_with_llm(
        self,
        ctx: ToolContext,
        package: EvidencePackage,
        *,
        llm_providers: list | None = None,
        correlation_boost: float = 0.0,
        refresh_tools: list[str] | None = None,
        settings: Any | None = None,
        cost_tracker: Any | None = None,
    ) -> AgentOpinion:
        """Run LLM tool loop when providers present; else deterministic tools + optional claim LLM."""
        from aaf.config import get_settings
        from agents.base import run_agent_llm_flow
        from agents.llm_tool_loop import run_llm_tool_loop

        cfg = settings or get_settings()

        if getattr(cfg, "phase1_static_agents", False):
            return await self.run_async(
                ctx, package, correlation_boost=correlation_boost, refresh_tools=refresh_tools
            )

        if llm_providers and cfg.guardrails_enabled:
            try:
                return await run_llm_tool_loop(
                    self,
                    ctx,
                    package,
                    llm_providers=llm_providers,
                    settings=cfg,
                    cost_tracker=cost_tracker,
                )
            except Exception:
                pass

        base = await self.run_async(
            ctx, package, correlation_boost=correlation_boost, refresh_tools=refresh_tools
        )
        if not llm_providers:
            return base

        def fallback() -> AgentOpinion:
            return base

        llm_opinion = run_agent_llm_flow(
            self.agent_id,
            package.records,
            self.system_prompt(),
            fallback,
            llm_providers=llm_providers,
        )
        llm_opinion.evidence = base.evidence or llm_opinion.evidence
        llm_opinion.raw_signals = {**base.raw_signals, **llm_opinion.raw_signals}
        called = base.raw_signals.get("tools_called")
        if called:
            llm_opinion.raw_signals["tools_called"] = called
            allowlist = [fn.__name__ for fn in self.tool_callables()]
            llm_opinion.raw_signals["tools_skipped"] = [
                name for name in allowlist if name not in called
            ]
        return llm_opinion

    async def run_async(
        self,
        ctx: ToolContext,
        package: EvidencePackage,
        *,
        correlation_boost: float = 0.0,
        refresh_tools: list[str] | None = None,
    ) -> AgentOpinion:
        tool_results = await self.run_tools(ctx, refresh_tools=refresh_tools)
        boost = correlation_boost or self.correlation_boost(tool_results)
        confidence = ConfidenceScorer.compute(
            tool_results,
            self.tool_weights(),
            staleness_hours=self.staleness_hours,
            penalty_factor=self.staleness_penalty,
            correlation_boost=boost,
        )
        confidence = self.apply_confidence_rules(confidence, tool_results)
        claim = self.generate_claim(tool_results, package)
        evidence = self.package_evidence(tool_results)
        theme = self.determine_risk_theme(tool_results, confidence)
        refs = evidence[:12] or [f"{self.agent_id}:baseline"]

        from agents.display import resolve_display_id

        allowlist = [fn.__name__ for fn in self.tool_callables()]
        called = [r.tool_name for r in tool_results]
        raw_signals = self.merge_raw_signals(tool_results)
        raw_signals["tools_called"] = called
        raw_signals["tools_skipped"] = [name for name in allowlist if name not in called]

        return AgentOpinion(
            agent_id=self.agent_id,
            display_id=resolve_display_id(self.agent_id),
            claim=claim,
            confidence=confidence,
            evidence_refs=refs,
            evidence=evidence,
            risk_theme=theme,
            raw_signals=raw_signals,
        )

    def stale_tool_names(self, tool_results: list[ToolResult]) -> list[str]:
        return [
            r.tool_name
            for r in tool_results
            if ConfidenceScorer.is_stale(r.captured_at, staleness_hours=self.staleness_hours)
        ]
