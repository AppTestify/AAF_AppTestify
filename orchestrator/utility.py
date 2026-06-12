"""Utility: business-aware action selection with U = w_perf*P + w_cost*Ci + w_risk*R."""

from __future__ import annotations

from aaf.config import Settings
from aaf.schema import AgentOpinion, EvidenceRecord, GovernanceAction, UtilityResult


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
        elif "pr" in k or "workflow" in k or "deploy" in k or "incident" in k:
            perf += sev
        else:
            risk += sev * 0.5
            perf += sev * 0.5
    return (
        min(1.0, perf / n),
        min(1.0, cost / n),
        min(1.0, risk / n),
    )


def _indices_from_opinions(
    evidence: list[EvidenceRecord],
    opinions: list[AgentOpinion] | None,
) -> tuple[float, float, float]:
    """Derive P, Ci, R indices from agent opinions when available."""
    perf_stress, cost_stress, risk_stress = _aggregate_signals(evidence)
    p_index = 1.0 - perf_stress
    r_index = 1.0 - risk_stress
    ci_index = 1.0 - cost_stress

    if opinions:
        by_id = {o.agent_id: o for o in opinions}
        devops = by_id.get("devops")
        finops = by_id.get("finops")
        devsecops = by_id.get("devsecops")
        pm = by_id.get("project_management")

        if devops:
            p_index = round(1.0 - devops.confidence, 4)
        if finops:
            ci_raw = finops.raw_signals.get("Ci")
            if ci_raw is not None:
                ci_index = float(ci_raw)
            else:
                ci_index = round(1.0 - finops.confidence, 4)
        if devsecops:
            r_index = round(1.0 - devsecops.confidence, 4)
        if pm and pm.confidence > 0.5:
            p_index = round(min(p_index, 1.0 - pm.confidence * 0.5), 4)

    return p_index, ci_index, r_index


def score_actions(
    evidence: list[EvidenceRecord],
    settings: Settings,
    opinions: list[AgentOpinion] | None = None,
) -> UtilityResult:
    perf, cost, risk = _aggregate_signals(evidence)
    p_index, ci_index, r_index = _indices_from_opinions(evidence, opinions)
    w_p, w_c, w_r = settings.w_perf, settings.w_cost, settings.w_risk
    weights_used = {"w_perf": w_p, "w_cost": w_c, "w_risk": w_r}
    global_u = round(w_p * p_index + w_c * ci_index + w_r * r_index, 4)

    def u_rollback() -> float:
        return w_p * perf + w_r * risk + w_c * 0.2 * cost

    def u_mitigate() -> float:
        return w_p * 0.8 * perf + w_r * 0.9 * risk + w_c * 0.3 * cost

    def u_scale() -> float:
        return w_p * 0.5 * perf + w_c * 0.9 * cost + w_r * 0.2 * risk

    def u_patch_block() -> float:
        return w_r * risk + w_p * 0.4 * perf + w_c * 0.2 * cost

    def u_hold_release() -> float:
        if opinions:
            return w_p * p_index + w_c * ci_index + w_r * r_index
        return w_r * risk + w_p * 0.35 * perf + w_c * 0.15 * cost

    def u_observe() -> float:
        inv = (perf + cost + risk) / 3.0
        return w_p * (1 - perf) * 0.3 + w_c * (1 - cost) * 0.3 + w_r * (1 - risk) * 0.3 + 0.2 * (1 - inv)

    scores = {
        GovernanceAction.ROLLBACK.value: u_rollback(),
        GovernanceAction.MITIGATE_MONITOR.value: u_mitigate(),
        GovernanceAction.SCALE_ADJUST.value: u_scale(),
        GovernanceAction.PATCH_BLOCK_RELEASE.value: u_patch_block(),
        GovernanceAction.HOLD_RELEASE.value: u_hold_release(),
        GovernanceAction.OBSERVE.value: u_observe(),
    }

    best_action = max(scores, key=scores.get)  # type: ignore[arg-type]
    utility_score = scores[best_action]

    return UtilityResult(
        recommended_action=GovernanceAction(best_action),
        utility_score=utility_score,
        scores_by_action=scores,
        weights_used=weights_used,
        perf_index=p_index,
        cost_index=ci_index,
        risk_index=r_index,
        global_utility=global_u,
    )
