"""ReAct-style LLM tool loop with per-call tool_scope_guard checks."""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from aaf.schema import AgentOpinion, EvidenceRecord, RiskTheme
from agents.schemas import EvidencePackage, ToolResult
from app.services.llm_runtime import invoke_json_with_failover
from guardrails.tool_scope_guard import append_tool_scope_event, check_tool_call
from tools.scoring import ConfidenceScorer

if TYPE_CHECKING:
    from aaf.config import Settings
    from agents.base_agent import BaseAgent
    from app.services.llm_runtime import ActiveProvider
    from tools.context import ToolContext


async def run_llm_tool_loop(
    agent: BaseAgent,
    ctx: ToolContext,
    package: EvidencePackage,
    *,
    llm_providers: list[ActiveProvider],
    settings: Settings,
    cost_tracker: LlmCostTracker | None = None,
) -> AgentOpinion:
    """Run up to max_tool_calls_per_agent tool invocations guided by LLM proposals."""
    from guardrails.llm_cost_tracker import LlmCostTracker as TrackerCls

    callables = agent.tool_callables()
    tool_by_name = {fn.__name__: fn for fn in callables}
    allowlist = list(tool_by_name.keys())
    max_calls = settings.max_tool_calls_per_agent
    tracker = cost_tracker or TrackerCls()

    tool_results: list[ToolResult] = []
    guardrail_events: list[dict[str, str]] = []
    call_index = 0
    done = False

    while call_index < max_calls and not done:
        if len(tracker.calls) >= settings.max_llm_calls_per_run:
            break
        proposal_prompt = _build_proposal_prompt(
            agent.agent_id,
            allowlist,
            tool_results,
            package.records,
            call_index,
            max_calls,
        )
        try:
            proposal, _meta = invoke_json_with_failover(
                llm_providers,
                proposal_prompt,
                system_prompt=agent.system_prompt(),
            )
            tracker.record_from_meta(
                phase="agent_tool_loop",
                agent_id=agent.agent_id,
                meta=_meta,
                prompt_text=proposal_prompt,
                completion_text=str(proposal),
            )
        except Exception:
            break

        if proposal.get("done") is True:
            done = True
            break

        tool_name = str(proposal.get("tool_name") or "").strip()
        if not tool_name:
            break

        scope_result = check_tool_call(agent.agent_id, tool_name, call_index=call_index, settings=settings)
        if scope_result.blocked or not scope_result.passed:
            for v in scope_result.violations:
                guardrail_events.append(
                    {"guard": "tool_scope_guard", "tool_name": tool_name, "message": v.message}
                )
            call_index += 1
            continue

        fn = tool_by_name.get(tool_name)
        if fn is None:
            guardrail_events.append(
                {
                    "guard": "tool_scope_guard",
                    "tool_name": tool_name,
                    "message": f"Unknown tool '{tool_name}' for agent '{agent.agent_id}'",
                }
            )
            call_index += 1
            continue

        result = await fn(ctx)
        tool_results.append(result)
        call_index += 1

    if not tool_results:
        tool_results = list(await agent.run_tools(ctx))

    boost = agent.correlation_boost(tool_results)
    confidence = ConfidenceScorer.compute(
        tool_results,
        agent.tool_weights(),
        staleness_hours=agent.staleness_hours,
        penalty_factor=agent.staleness_penalty,
        correlation_boost=boost,
    )
    confidence = agent.apply_confidence_rules(confidence, tool_results)
    claim = agent.generate_claim(tool_results, package)
    evidence = agent.package_evidence(tool_results)
    theme = agent.determine_risk_theme(tool_results, confidence)
    refs = evidence[:12] or [f"{agent.agent_id}:baseline"]
    raw_signals = agent.merge_raw_signals(tool_results)
    called = [r.tool_name for r in tool_results]
    raw_signals["tools_called"] = called
    raw_signals["tools_skipped"] = [name for name in allowlist if name not in called]
    for event in guardrail_events:
        raw_signals = append_tool_scope_event(
            raw_signals,
            tool_name=event["tool_name"],
            message=event["message"],
        )

    from agents.display import resolve_display_id

    return AgentOpinion(
        agent_id=agent.agent_id,
        display_id=resolve_display_id(agent.agent_id),
        claim=claim,
        confidence=confidence,
        evidence_refs=refs,
        evidence=evidence,
        risk_theme=theme,
        raw_signals=raw_signals,
    )


def _build_proposal_prompt(
    agent_id: str,
    allowlist: list[str],
    tool_results: list[ToolResult],
    evidence: list[EvidenceRecord],
    call_index: int,
    max_calls: int,
) -> str:
    results_summary = [
        {"tool": r.tool_name, "signal": r.signal, "lines": r.evidence_lines[:2]} for r in tool_results
    ]
    evidence_summary = [{"source": e.source, "kind": e.kind, "summary": e.summary[:120]} for e in evidence[:8]]
    return (
        f"You are agent '{agent_id}'. Choose the next governance tool to run or finish.\n"
        f"Allowlisted tools: {json.dumps(allowlist)}\n"
        f"Call index: {call_index} (max {max_calls})\n"
        f"Evidence context: {json.dumps(evidence_summary)}\n"
        f"Tools already run: {json.dumps(results_summary)}\n"
        "Return JSON only: {\"tool_name\": \"<name from allowlist>\", \"done\": false} "
        "or {\"done\": true} when sufficient tools have run."
    )
