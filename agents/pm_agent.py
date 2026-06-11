"""PM agent — sprint delivery, blockers, defects, velocity."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import TYPE_CHECKING

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base_agent import BaseAgent
from agents.schemas import EvidencePackage, ToolResult
from tools.context import ToolContext, build_tool_context
from tools.pm.blockers import count_blockers
from tools.pm.error_rate import check_error_rate
from tools.pm.latency_check import check_latency
from tools.pm.open_defects import get_open_defects
from tools.pm.queue_depth import check_queue_depth
from tools.pm.sprint_status import get_sprint_status
from tools.pm.velocity_risk import calc_velocity_risk

if TYPE_CHECKING:
    from aaf.config import Settings
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a Project Management and agile delivery governance agent. "
    "Assess project milestone progress, sprint metrics, issue blockers, and ticket delays."
)


class PMAgent(BaseAgent):
    agent_id = "project_management"
    risk_theme_default = RiskTheme.DELIVERY_RISK

    def system_prompt(self) -> str:
        return SYSTEM_PROMPT
    staleness_hours = 4.0
    staleness_penalty = 0.5

    def tool_weights(self) -> dict[str, float]:
        return {
            "count_blockers": 0.30,
            "get_open_defects": 0.20,
            "calc_velocity_risk": 0.15,
            "get_sprint_status": 0.10,
            "check_latency": 0.10,
            "check_error_rate": 0.10,
            "check_queue_depth": 0.05,
        }

    def tool_callables(self):
        return [
            get_sprint_status,
            count_blockers,
            get_open_defects,
            calc_velocity_risk,
            check_latency,
            check_error_rate,
            check_queue_depth,
        ]

    def generate_claim(self, tool_results: list[ToolResult], package: EvidencePackage) -> str:
        by_name = {r.tool_name: r for r in tool_results}
        blockers = by_name.get("count_blockers")
        defects = by_name.get("get_open_defects")
        velocity = by_name.get("calc_velocity_risk")

        blocked_count = int((blockers.raw_signals.get("blocked_count", 0) if blockers else 0))
        if blocked_count >= 5:
            return "Sprint has critical blocker load — action required regardless of velocity."
        if blocked_count > 0:
            return "Sprint or delivery items are blocked or overdue."
        if defects and int(defects.raw_signals.get("open_bugs_high", 0)) > 0:
            return "Unresolved high/critical defects may affect release readiness."
        if velocity and velocity.raw_signals.get("pace_flag"):
            return "Sprint velocity is at risk — committed work may not complete on time."
        return "Delivery signals appear stable."

    def apply_confidence_rules(self, confidence: float, tool_results: list[ToolResult]) -> float:
        by_name = {r.tool_name: r for r in tool_results}
        blockers = by_name.get("count_blockers")
        if blockers and int(blockers.raw_signals.get("blocked_count", 0)) >= 5:
            return max(confidence, 0.85)
        return confidence


_agent = PMAgent()


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
