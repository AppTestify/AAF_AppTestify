"""DevSecOps agent — CVEs, secrets, policy violations, dependencies."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import TYPE_CHECKING

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.base_agent import BaseAgent
from agents.schemas import EvidencePackage, ToolResult
from tools.context import ToolContext, build_tool_context
from tools.devsecops import audit_dependencies, check_policy_violations, scan_cves, scan_secrets

if TYPE_CHECKING:
    from aaf.config import Settings
    from app.services.llm_runtime import ActiveProvider

SYSTEM_PROMPT = (
    "You are a DevSecOps and cloud security governance agent. "
    "Assess security compliance violations, vulnerability scans, secret exposures, and access control anomalies."
)


class DevSecOpsAgent(BaseAgent):
    agent_id = "devsecops"
    risk_theme_default = RiskTheme.SECURITY_RISK

    def system_prompt(self) -> str:
        return SYSTEM_PROMPT
    staleness_hours = 4.0
    staleness_penalty = 0.5

    def tool_weights(self) -> dict[str, float]:
        return {
            "scan_cves": 0.40,
            "scan_secrets": 0.30,
            "check_policy_violations": 0.20,
            "audit_dependencies": 0.10,
        }

    def tool_callables(self):
        return [scan_cves, scan_secrets, check_policy_violations, audit_dependencies]

    def generate_claim(self, tool_results: list[ToolResult], package: EvidencePackage) -> str:
        by_name = {r.tool_name: r for r in tool_results}
        cves = by_name.get("scan_cves")
        secrets = by_name.get("scan_secrets")
        if secrets and secrets.raw_signals.get("secrets_detected"):
            return "Secret exposure detected — shipping is blocked from a security standpoint."
        if cves and int(cves.raw_signals.get("critical_count", 0)) > 0:
            return "Critical CVEs present — release should be blocked."
        if cves and int(cves.raw_signals.get("high_count", 0)) > 0:
            return "High-severity vulnerabilities require attention before release."
        policy = by_name.get("check_policy_violations")
        if policy and int(policy.raw_signals.get("violation_count", 0)) > 0:
            return "Security or policy risk indicated."
        return "No security policy violations flagged in evidence."

    def apply_confidence_rules(self, confidence: float, tool_results: list[ToolResult]) -> float:
        by_name = {r.tool_name: r for r in tool_results}
        cves = by_name.get("scan_cves")
        secrets = by_name.get("scan_secrets")
        critical = int(cves.raw_signals.get("critical_count", 0)) if cves else 0
        if critical > 0 or (secrets and secrets.raw_signals.get("secrets_detected")):
            return max(confidence, 0.90)
        return confidence


_agent = DevSecOpsAgent()


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
