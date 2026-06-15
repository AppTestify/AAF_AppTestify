"""Consensus: measure agreement between agent opinions."""

from __future__ import annotations

from collections import Counter

from aaf.schema import AgentOpinion, ConsensusResult, RiskTheme


def _theme_compat(a: RiskTheme, b: RiskTheme) -> bool:
    if a == b:
        return True
    # Related operational families align for consensus boost
    related = {
        frozenset({RiskTheme.OPERATIONAL_RISK, RiskTheme.RELIABILITY_RISK}),
        frozenset({RiskTheme.DELIVERY_RISK, RiskTheme.OPERATIONAL_RISK}),
        frozenset({RiskTheme.COST_RISK, RiskTheme.OPERATIONAL_RISK}),
    }
    return frozenset({a, b}) in related


def compute_consensus(opinions: list[AgentOpinion]) -> ConsensusResult:
    """
    consensus_score in [0,1]:
    - Base on dominant risk theme frequency
    - Weight each vote by confidence
    - Penalize conflicting themes (incompatible pairs)
    """
    if not opinions:
        return ConsensusResult(
            consensus_score=0.0,
            theme_counts={},
            dominant_theme=None,
            notes="No agent opinions",
        )

    weighted: Counter[str] = Counter()
    for o in opinions:
        key = o.risk_theme.value
        weighted[key] += max(0.0, o.confidence)

    theme_counts = {k: int(round(v * 10)) for k, v in weighted.items()}  # display-friendly
    dominant = max(weighted.items(), key=lambda x: x[1])[0]
    dominant_theme = RiskTheme(dominant)

    # Conflict penalty: pair opinions with incompatible themes
    n = len(opinions)
    conflict_pairs = 0
    total_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            total_pairs += 1
            if not _theme_compat(opinions[i].risk_theme, opinions[j].risk_theme):
                conflict_pairs += 1

    conflict_ratio = conflict_pairs / total_pairs if total_pairs else 0.0

    # Dominant share of weighted mass
    total_weight = sum(weighted.values()) or 1.0
    dominant_share = weighted[dominant] / total_weight

    # Blend: agreement on dominant theme minus conflicts
    raw = 0.7 * dominant_share + 0.3 * (1.0 - conflict_ratio)
    consensus_score = max(0.0, min(1.0, raw))

    notes = f"dominant={dominant}, conflicts={conflict_pairs}/{total_pairs}"
    return ConsensusResult(
        consensus_score=consensus_score,
        theme_counts=theme_counts,
        dominant_theme=dominant_theme,
        notes=notes,
    )


def compute_consensus_phase1(opinions: list[AgentOpinion]) -> ConsensusResult:
    """
    Phase 1 spec formula: C = 0.5 * mean(confidences) + 0.5 * domain_agreement
    """
    if not opinions:
        return ConsensusResult(
            consensus_score=0.0,
            theme_counts={},
            dominant_theme=None,
            notes="No agent opinions",
        )

    mean_conf = sum(o.confidence for o in opinions) / len(opinions)

    n = len(opinions)
    conflict_pairs = 0
    total_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            total_pairs += 1
            if not _theme_compat(opinions[i].risk_theme, opinions[j].risk_theme):
                conflict_pairs += 1

    conflict_ratio = conflict_pairs / total_pairs if total_pairs else 0.0
    domain_agreement = 1.0 - conflict_ratio

    consensus_score = 0.5 * mean_conf + 0.5 * domain_agreement

    # Still calculate dominant theme for the ConsensusResult object
    weighted: Counter[str] = Counter()
    for o in opinions:
        weighted[o.risk_theme.value] += max(0.0, o.confidence)
    theme_counts = {k: int(round(v * 10)) for k, v in weighted.items()}
    dominant = max(weighted.items(), key=lambda x: x[1])[0]

    notes = f"mean_conf={mean_conf:.2f}, agreement={domain_agreement:.2f}"
    return ConsensusResult(
        consensus_score=consensus_score,
        theme_counts=theme_counts,
        dominant_theme=RiskTheme(dominant),
        notes=notes,
    )
