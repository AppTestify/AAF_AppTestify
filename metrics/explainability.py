"""Explainability index (XI) — heuristic auditability score."""

from __future__ import annotations

from aaf.schema import (
    AgentOpinion,
    ConsensusResult,
    EvidenceRecord,
    ExplainabilityResult,
    UtilityResult,
)


def compute_xi(
    *,
    evidence: list[EvidenceRecord],
    opinions: list[AgentOpinion],
    consensus: ConsensusResult,
    utility: UtilityResult,
    explanation_text: str,
) -> ExplainabilityResult:
    checks: dict[str, bool] = {}
    checks["has_evidence"] = len(evidence) > 0
    checks["has_opinions"] = len(opinions) >= 3
    checks["consensus_documented"] = consensus.consensus_score >= 0.0 and len(consensus.notes or "") > 0
    checks["utility_margin"] = _utility_margin(utility) > 0.02
    checks["explanation_sections"] = (
        "Consensus" in explanation_text and "Recommended action" in explanation_text
    )
    checks["scores_auditable"] = len(utility.scores_by_action) >= 3

    passed = sum(1 for v in checks.values() if v)
    xi = passed / max(1, len(checks))
    return ExplainabilityResult(xi_score=round(xi, 3), checks=checks)


def _utility_margin(utility: UtilityResult) -> float:
    scores = list(utility.scores_by_action.values())
    if len(scores) < 2:
        return 0.0
    s = sorted(scores, reverse=True)
    return s[0] - s[1]
