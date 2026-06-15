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
    from guardrails.llm_cost_tracker import LlmCostTracker


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
    reasoning_steps: list[dict[str, Any]] = []
    tools_called: list[str] = []
    
    call_index = 0
    done = False
    final_claim = ""
    final_confidence = 0.0
    final_theme_str = ""

    # 1. Get tool definitions with descriptions (schemas)
    tool_schemas = []
    for tname, fn in tool_by_name.items():
        doc = fn.__doc__ or ""
        tool_schemas.append({
            "name": tname,
            "description": doc.strip().split("\n")[0]
        })

    while call_index < max_calls and not done:
        if len(tracker.calls) >= settings.max_llm_calls_per_run:
            break
        proposal_prompt = _build_proposal_prompt(
            agent.agent_id,
            tool_schemas,
            reasoning_steps,
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

        thought = str(proposal.get("thought") or "")
        done = bool(proposal.get("done"))
        tool_name = str(proposal.get("tool_name") or "").strip()

        if done:
            final_claim = str(proposal.get("claim") or "")
            try:
                final_confidence = float(proposal.get("confidence") if proposal.get("confidence") is not None else 0.0)
            except (ValueError, TypeError):
                final_confidence = 0.0
            final_theme_str = str(proposal.get("risk_theme") or "")
            
            reasoning_steps.append({
                "step": call_index + 1,
                "thought": thought,
                "done": True,
                "claim": final_claim,
                "confidence": final_confidence,
            })
            break

        if not tool_name:
            break

        # Check scope guard
        scope_result = check_tool_call(agent.agent_id, tool_name, call_index=call_index, settings=settings)
        blocked = False
        if scope_result.blocked or not scope_result.passed:
            blocked = True
            for v in scope_result.violations:
                guardrail_events.append(
                    {"guard": "tool_scope_guard", "tool_name": tool_name, "message": v.message}
                )

        fn = tool_by_name.get(tool_name)
        if fn is None:
            blocked = True
            guardrail_events.append(
                {
                    "guard": "tool_scope_guard",
                    "tool_name": tool_name,
                    "message": f"Unknown tool '{tool_name}' for agent '{agent.agent_id}'",
                }
            )

        if not blocked and fn is not None:
            result = await fn(ctx)
            tool_results.append(result)
            tools_called.append(tool_name)
            
            reasoning_steps.append({
                "step": call_index + 1,
                "thought": thought,
                "tool_called": tool_name,
                "result_signal": result.signal,
                "done": False,
            })
        else:
            reasoning_steps.append({
                "step": call_index + 1,
                "thought": thought,
                "tool_called": tool_name,
                "blocked": True,
                "done": False,
            })

        call_index += 1

    if not tool_results:
        tool_results = list(await agent.run_tools(ctx))
        tools_called = [r.tool_name for r in tool_results]

    # 2. Final Assessment Fallback
    if not final_claim or final_confidence == 0.0:
        results_summary = [
            {"tool": r.tool_name, "signal": r.signal, "lines": r.evidence_lines[:3]} for r in tool_results
        ]
        final_prompt = (
            f"You are agent '{agent.agent_id}'. You have executed the following governance tools:\n"
            f"Reasoning steps: {json.dumps(reasoning_steps, indent=2)}\n"
            f"Tool execution results: {json.dumps(results_summary, indent=2)}\n"
            f"Evidence records: {json.dumps([{'source': e.source, 'kind': e.kind, 'summary': e.summary[:120]} for e in package.records[:10]], indent=2)}\n"
            "Please provide your final claim, confidence (0.0 to 1.0), and dominant risk_theme (one of: operational_risk, cost_risk, security_risk, delivery_risk, reliability_risk, low_risk, unknown).\n"
            "Return JSON only: {\"claim\": \"your final assessment/opinion\", \"confidence\": 0.85, \"risk_theme\": \"low_risk\"}"
        )
        try:
            resp, _meta = invoke_json_with_failover(
                llm_providers,
                final_prompt,
                system_prompt=agent.system_prompt(),
            )
            tracker.record_from_meta(
                phase="agent_final_assessment",
                agent_id=agent.agent_id,
                meta=_meta,
                prompt_text=final_prompt,
                completion_text=str(resp),
            )
            if not final_claim:
                final_claim = str(resp.get("claim") or "")
            if final_confidence == 0.0:
                try:
                    final_confidence = float(resp.get("confidence") if resp.get("confidence") is not None else 0.0)
                except (ValueError, TypeError):
                    final_confidence = 0.0
            if not final_theme_str:
                final_theme_str = str(resp.get("risk_theme") or "")
        except Exception:
            pass

    # Fallbacks if LLM calls failed completely
    if not final_claim:
        final_claim = agent.generate_claim(tool_results, package)
    if final_confidence == 0.0:
        boost = agent.correlation_boost(tool_results)
        final_confidence = ConfidenceScorer.compute(
            tool_results,
            agent.tool_weights(),
            staleness_hours=agent.staleness_hours,
            penalty_factor=agent.staleness_penalty,
            correlation_boost=boost,
        )
        final_confidence = agent.apply_confidence_rules(final_confidence, tool_results)

    # Resolve risk theme
    theme = RiskTheme.UNKNOWN
    if final_theme_str:
        for t in RiskTheme:
            if t.value.lower() == final_theme_str.lower().strip():
                theme = t
                break
    if theme == RiskTheme.UNKNOWN:
        theme = agent.determine_risk_theme(tool_results, final_confidence)

    # Package evidence & details
    evidence = agent.package_evidence(tool_results)
    refs = evidence[:12] or [f"{agent.agent_id}:baseline"]
    
    raw_signals = agent.merge_raw_signals(tool_results)
    called_set = set(tools_called)
    raw_signals["tools_called"] = tools_called
    raw_signals["tools_skipped"] = [name for name in allowlist if name not in called_set]
    raw_signals["skipped_tools"] = raw_signals["tools_skipped"]
    raw_signals["reasoning_steps"] = reasoning_steps
    
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
        claim=final_claim,
        confidence=final_confidence,
        evidence_refs=refs,
        evidence=evidence,
        risk_theme=theme,
        raw_signals=raw_signals,
    )


def _build_proposal_prompt(
    agent_id: str,
    tool_schemas: list[dict[str, str]],
    reasoning_steps: list[dict[str, Any]],
    tool_results: list[ToolResult],
    evidence: list[EvidenceRecord],
    call_index: int,
    max_calls: int,
) -> str:
    results_summary = [
        {"tool": r.tool_name, "signal": r.signal, "lines": r.evidence_lines[:3]} for r in tool_results
    ]
    evidence_summary = [{"source": e.source, "kind": e.kind, "summary": e.summary[:120]} for e in evidence[:10]]
    return (
        f"You are agent '{agent_id}'. Choose the next governance tool to run or finish.\n"
        f"Available tools and descriptions: {json.dumps(tool_schemas, indent=2)}\n"
        f"Current step / call index: {call_index} (max limit is {max_calls})\n"
        f"Initial evidence context: {json.dumps(evidence_summary, indent=2)}\n"
        f"Reasoning history so far: {json.dumps(reasoning_steps, indent=2)}\n"
        f"Tool results obtained so far: {json.dumps(results_summary, indent=2)}\n"
        "Instructions: Return a JSON object with: \n"
        "{\n"
        "  \"thought\": \"reasoning about what tool to run next or whether we have enough info\",\n"
        "  \"tool_name\": \"<name of tool from available tools, or null if done is true>\",\n"
        "  \"done\": false\n"
        "}\n"
        "If you have gathered sufficient information to evaluate release readiness, set \"done\" to true and provide your final assessment:\n"
        "{\n"
        "  \"thought\": \"final summary reasoning\",\n"
        "  \"done\": true,\n"
        "  \"claim\": \"your final claim/opinion about release safety/readiness\",\n"
        "  \"confidence\": 0.85,\n"
        "  \"risk_theme\": \"low_risk\"\n"
        "}"
    )
