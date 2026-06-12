"""Run all domain agents on normalized evidence (parallel async)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from aaf.schema import AgentOpinion, EvidenceRecord
from agents import devops, devsecops, finops, pm_agent
from agents.display import resolve_display_id
from tools.context import ToolContext, build_tool_context

if TYPE_CHECKING:
    from aaf.config import Settings
    from app.services.llm_runtime import ActiveProvider

_AGENT_RUNNERS = {
    "devops": devops.run_async,
    "finops": finops.run_async,
    "devsecops": devsecops.run_async,
    "project_management": pm_agent.run_async,
}


def _with_display_id(opinion: AgentOpinion) -> AgentOpinion:
    if opinion.display_id:
        return opinion
    return opinion.model_copy(update={"display_id": resolve_display_id(opinion.agent_id)})


async def run_agents_async(
    evidence: list[EvidenceRecord],
    agent_ids: list[str],
    *,
    tool_ctx: ToolContext | None = None,
    settings: Settings | None = None,
    llm_providers: list[ActiveProvider] | None = None,
    refresh_tools: list[str] | None = None,
    cost_tracker: Any | None = None,
) -> list[AgentOpinion]:
    ctx = tool_ctx
    if ctx is None:
        from aaf.config import get_settings

        ctx = build_tool_context(settings or get_settings())

    tasks = []
    for agent_id in agent_ids:
        runner = _AGENT_RUNNERS.get(agent_id)
        if runner is None:
            continue
        tasks.append(
            runner(
                evidence,
                tool_ctx=ctx,
                settings=settings,
                llm_providers=llm_providers,
                refresh_tools=refresh_tools,
                cost_tracker=cost_tracker,
            )
        )
    if not tasks:
        return []
    results = await asyncio.gather(*tasks)
    return [_with_display_id(op) for op in results]


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

    return await run_agents_async(
        evidence,
        ["devops", "finops", "devsecops", "project_management"],
        tool_ctx=ctx,
        settings=settings,
        llm_providers=llm_providers,
    )


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
