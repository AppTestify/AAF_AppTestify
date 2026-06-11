"""FinOps agent — cloud cost, budget, scaling, unit cost, RI coverage."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import TYPE_CHECKING

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base_agent import BaseAgent
from agents.schemas import EvidencePackage, ToolResult
from tools.context import ToolContext, build_tool_context
from tools.finops import (
    calc_unit_cost,
    check_budget_pace,
    detect_scaling_anomaly,
    get_ri_coverage,
    get_spend_trend,
)
from tools.finops.reasoning import compute_ci_score, generate_cost_claim, package_finops_evidence
from tools.finops.reasoning.efficiency_scorer import finops_correlation_boost

if TYPE_CHECKING:
    from aaf.config import Settings
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a FinOps and cloud cost governance agent. "
    "Assess cloud infrastructure costs, budget variances, and cost anomaly events."
)


class FinOpsAgent(BaseAgent):
    agent_id = "finops"
    risk_theme_default = RiskTheme.COST_RISK

    def system_prompt(self) -> str:
        return SYSTEM_PROMPT
    staleness_hours = 6.0
    staleness_penalty = 0.4

    def tool_weights(self) -> dict[str, float]:
        return {
            "get_spend_trend": 0.30,
            "check_budget_pace": 0.25,
            "detect_scaling_anomaly": 0.20,
            "calc_unit_cost": 0.15,
            "get_ri_coverage": 0.10,
        }

    def tool_callables(self):
        return [
            get_spend_trend,
            check_budget_pace,
            detect_scaling_anomaly,
            calc_unit_cost,
            get_ri_coverage,
        ]

    def generate_claim(self, tool_results: list[ToolResult], package: EvidencePackage) -> str:
        return generate_cost_claim(tool_results)

    def package_evidence(self, tool_results: list[ToolResult], *, max_lines: int = 6) -> list[str]:
        return package_finops_evidence(tool_results, max_lines=max_lines)

    def correlation_boost(self, tool_results: list[ToolResult]) -> float:
        return finops_correlation_boost(tool_results)

    def merge_raw_signals(self, tool_results: list[ToolResult]) -> dict:
        merged = super().merge_raw_signals(tool_results)
        boost = finops_correlation_boost(tool_results)
        merged["Ci"] = compute_ci_score(tool_results, correlation_boost=boost)
        merged["cost_efficiency_index"] = merged["Ci"]
        return merged


_agent = FinOpsAgent()


def _sync_await(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


async def run_async(
    evidence: list[EvidenceRecord],
    *,
    tool_ctx: ToolContext | None = None,
    settings: Settings | None = None,
    llm_providers: list[ActiveProvider] | None = None,
) -> AgentOpinion:
    from aaf.config import get_settings

    ctx = tool_ctx or build_tool_context(settings or get_settings())
    package = EvidencePackage(records=evidence)
    if llm_providers:
        return await _agent.run_with_llm(ctx, package, llm_providers=llm_providers)
    return await _agent.run_async(ctx, package)


def run(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
    *,
    tool_ctx: ToolContext | None = None,
) -> AgentOpinion:
    return _sync_await(run_async(evidence, tool_ctx=tool_ctx, llm_providers=llm_providers))
