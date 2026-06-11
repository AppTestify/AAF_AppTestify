"""Run all domain agents on normalized evidence (parallel async)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from aaf.schema import AgentOpinion, EvidenceRecord
from agents import devops, devsecops, finops, pm_agent
from tools.context import ToolContext, build_tool_context

if TYPE_CHECKING:
    from aaf.config import Settings
    from app.services.llm_runtime import ActiveProvider


async def run_all_agents_async(
    evidence: list[EvidenceRecord],
    *,
    tool_ctx: ToolContext | None = None,
    settings: Settings | None = None,
    llm_providers: list[ActiveProvider] | None = None,
) -> list[AgentOpinion]:
    ctx = tool_ctx
    if ctx is None:
        from aaf.config import get_settings

        ctx = build_tool_context(settings or get_settings())

    results = await asyncio.gather(
        devops.run_async(evidence, tool_ctx=ctx, settings=settings, llm_providers=llm_providers),
        finops.run_async(evidence, tool_ctx=ctx, settings=settings, llm_providers=llm_providers),
        devsecops.run_async(evidence, tool_ctx=ctx, settings=settings, llm_providers=llm_providers),
        pm_agent.run_async(evidence, tool_ctx=ctx, settings=settings, llm_providers=llm_providers),
    )
    return list(results)


def run_all_agents(
    evidence: list[EvidenceRecord],
    llm_providers: list[ActiveProvider] | None = None,
    *,
    tool_ctx: ToolContext | None = None,
    settings: Settings | None = None,
) -> list[AgentOpinion]:
    return asyncio.run(
        run_all_agents_async(
            evidence,
            tool_ctx=tool_ctx,
            settings=settings,
            llm_providers=llm_providers,
        )
    )
