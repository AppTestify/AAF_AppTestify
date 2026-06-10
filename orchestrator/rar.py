"""RAR: Re-Grounded Agentic Reasoning — retry when consensus is low."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable

from aaf.schema import AgentOpinion, ConsensusResult, EvidenceRecord, RARResult

from orchestrator.consensus import compute_consensus


async def run_rar_loop_async(
    *,
    initial_evidence: list[EvidenceRecord],
    initial_opinions: list[AgentOpinion],
    tau: float,
    max_loops: int,
    rerun_agents: Callable[[list[EvidenceRecord], int], list[AgentOpinion]]
    | Callable[[list[EvidenceRecord], int], Awaitable[list[AgentOpinion]]],
    enrich_evidence: Callable[[list[EvidenceRecord], int], list[EvidenceRecord]],
    live_refresh_evidence: Callable[[], Awaitable[list[EvidenceRecord]]] | None = None,
) -> tuple[list[AgentOpinion], RARResult, ConsensusResult]:
    """
    If consensus < tau, enrich evidence (or live-refresh connectors) and rerun agents up to max_loops.
    """
    consensus_before_result = compute_consensus(initial_opinions)
    consensus_before = consensus_before_result.consensus_score

    opinions = list(initial_opinions)
    evidence = list(initial_evidence)
    reground_notes: list[str] = []
    loops = 0
    triggered = consensus_before < tau

    if not triggered:
        return opinions, RARResult(
            rar_triggered=False,
            rar_loops=0,
            consensus_before=consensus_before,
            consensus_after=consensus_before,
            reground_notes=[],
        ), consensus_before_result

    current = consensus_before
    while loops < max_loops and current < tau:
        loops += 1
        if live_refresh_evidence is not None:
            evidence = await live_refresh_evidence()
            reground_notes.append(f"RAR loop {loops}: live connector refresh, count={len(evidence)}")
        else:
            evidence = enrich_evidence(evidence, loops)
            reground_notes.append(f"RAR loop {loops}: evidence enriched, count={len(evidence)}")
        rerun_result = rerun_agents(evidence, loops)
        opinions = await rerun_result if inspect.isawaitable(rerun_result) else rerun_result
        cr = compute_consensus(opinions)
        current = cr.consensus_score

    final_consensus = compute_consensus(opinions)
    return opinions, RARResult(
        rar_triggered=True,
        rar_loops=loops,
        consensus_before=consensus_before,
        consensus_after=final_consensus.consensus_score,
        reground_notes=reground_notes,
    ), final_consensus


def merge_reground_stub(evidence: list[EvidenceRecord], loop: int) -> list[EvidenceRecord]:
    """Placeholder enricher used only if pipeline does not override."""
    extra = EvidenceRecord(
        source="system",
        kind="rar_reground",
        summary=f"Synthetic regrounded context (loop {loop})",
        severity=0.3,
        metadata={"loop": loop},
    )
    return [*evidence, extra]
