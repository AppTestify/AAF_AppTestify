"""Utility: business-aware action selection."""

from __future__ import annotations

from aaf.config import Settings
from aaf.schema import EvidenceRecord, GovernanceAction, UtilityResult


def _aggregate_signals(evidence: list[EvidenceRecord]) -> tuple[float, float, float]:
    """Return (perf_stress, cost_stress, risk_stress) in [0,1]."""
    perf = 0.0
    cost = 0.0
    risk = 0.0
    n = max(1, len(evidence))
    for e in evidence:
        sev = e.severity
        k = e.kind.lower()
        if "cost" in k or "finops" in e.source or "spend" in k:
            cost += sev
        elif "security" in k or "policy" in k or "vuln" in k:
            risk += sev
        elif "pr" in k or "workflow" in k or "deploy" in k or "sre" in e.source or "incident" in k:
            perf += sev
        else:
            risk += sev * 0.5
            perf += sev * 0.5
    return (
        min(1.0, perf / n),
        min(1.0, cost / n),
        min(1.0, risk / n),
    )


def score_actions(
    evidence: list[EvidenceRecord],
    settings: Settings,
) -> UtilityResult:
    perf, cost, risk = _aggregate_signals(evidence)
    w_p, w_c, w_r = settings.w_perf, settings.w_cost, settings.w_risk
    weights_used = {"w_perf": w_p, "w_cost": w_c, "w_risk": w_r}

    # Action affinity: how well each action matches stress profile
    def u_rollback() -> float:
        return w_p * perf + w_r * risk + w_c * 0.2 * cost

    def u_mitigate() -> float:
        return w_p * 0.8 * perf + w_r * 0.9 * risk + w_c * 0.3 * cost

    def u_scale() -> float:
        return w_p * 0.5 * perf + w_c * 0.9 * cost + w_r * 0.2 * risk

    def u_patch_block() -> float:
        return w_r * risk + w_p * 0.4 * perf + w_c * 0.2 * cost

    def u_observe() -> float:
        # Prefer observe when all stresses low
        inv = (perf + cost + risk) / 3.0
        return w_p * (1 - perf) * 0.3 + w_c * (1 - cost) * 0.3 + w_r * (1 - risk) * 0.3 + 0.2 * (1 - inv)

    scores = {
        GovernanceAction.ROLLBACK.value: u_rollback(),
        GovernanceAction.MITIGATE_MONITOR.value: u_mitigate(),
        GovernanceAction.SCALE_ADJUST.value: u_scale(),
        GovernanceAction.PATCH_BLOCK_RELEASE.value: u_patch_block(),
        GovernanceAction.OBSERVE.value: u_observe(),
    }

    best_action = max(scores, key=scores.get)  # type: ignore[arg-type]
    utility_score = scores[best_action]

    return UtilityResult(
        recommended_action=GovernanceAction(best_action),
        utility_score=utility_score,
        scores_by_action=scores,
        weights_used=weights_used,
    )
