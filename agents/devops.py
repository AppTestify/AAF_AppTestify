"""DevOps agent — CI/CD, deployments, rollbacks, branch protection."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import TYPE_CHECKING

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base_agent import BaseAgent
from agents.schemas import EvidencePackage, ToolResult
from tools.context import ToolContext, build_tool_context
from tools.devops import check_branch_protection, detect_rollbacks, get_ci_status, get_deploy_history

if TYPE_CHECKING:
    from aaf.config import Settings
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a DevOps and release engineering governance agent. "
    "Assess risks associated with CI/CD pipelines, code repository events, and PR activities."
)


class DevOpsAgent(BaseAgent):
    agent_id = "devops"
    risk_theme_default = RiskTheme.OPERATIONAL_RISK
    staleness_hours = 4.0
    staleness_penalty = 0.5

    def tool_weights(self) -> dict[str, float]:
        return {
            "get_ci_status": 0.35,
            "get_deploy_history": 0.25,
            "detect_rollbacks": 0.25,
            "check_branch_protection": 0.15,
        }

    def tool_callables(self):
        return [get_ci_status, get_deploy_history, detect_rollbacks, check_branch_protection]

    def generate_claim(self, tool_results: list[ToolResult], package: EvidencePackage) -> str:
        by_name = {r.tool_name: r for r in tool_results}
        ci = by_name.get("get_ci_status")
        rollback = by_name.get("detect_rollbacks")
        protection = by_name.get("check_branch_protection")

        if ci and ci.raw_signals.get("blocking_check"):
            return "CI/CD or workflow failures detected — release branch may be unsafe to merge."
        if rollback and int(rollback.raw_signals.get("rollback_24h", 0)) > 0:
            return "Recent rollback events indicate elevated deployment risk."
        if protection and not protection.raw_signals.get("checks_pass", True):
            return "Branch protection gates not fully satisfied."
        deploy = by_name.get("get_deploy_history")
        if deploy and float(deploy.raw_signals.get("change_fail_rate", 0)) > 0.3:
            return "Deployment change failure rate is elevated."
        return "Release branch appears safe to merge from DevOps signals."

    def determine_risk_theme(self, tool_results: list[ToolResult], confidence: float) -> RiskTheme:
        if confidence < 0.35:
            return RiskTheme.LOW_RISK
        by_name = {r.tool_name: r for r in tool_results}
        ci = by_name.get("get_ci_status")
        if ci and ci.raw_signals.get("blocking_check"):
            return RiskTheme.OPERATIONAL_RISK
        return RiskTheme.DELIVERY_RISK if confidence > 0.55 else RiskTheme.OPERATIONAL_RISK


_agent = DevOpsAgent()


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
) -> AgentOpinion:
    from aaf.config import get_settings

    ctx = tool_ctx or build_tool_context(settings or get_settings())
    package = EvidencePackage(records=evidence)
    return await _agent.run_async(ctx, package)


def run(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
    *,
    tool_ctx: ToolContext | None = None,
) -> AgentOpinion:
    del llm_providers  # Tool-weighted scoring is primary; LLM optional at pipeline level
    return _sync_await(run_async(evidence, tool_ctx=tool_ctx))
