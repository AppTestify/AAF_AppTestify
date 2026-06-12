"""Agent output guardrail — schema validation and confidence bounds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from aaf.schema import AgentOpinion, RiskTheme
from guardrails.types import GuardrailResult, GuardrailViolation

if TYPE_CHECKING:
    from aaf.config import Settings


def _degraded_opinion(opinion: AgentOpinion, violations: list[GuardrailViolation]) -> AgentOpinion:
    events = list(opinion.raw_signals.get("guardrail_events") or [])
    events.append(
        {
            "guard": "agent_output_guard",
            "violations": [v.model_dump() for v in violations],
        }
    )
    return AgentOpinion(
        agent_id=opinion.agent_id,
        claim="Agent output failed validation; using conservative degraded assessment.",
        confidence=0.3,
        evidence_refs=opinion.evidence_refs[:3],
        evidence=opinion.evidence[:3],
        risk_theme=RiskTheme.UNKNOWN,
        raw_signals={**opinion.raw_signals, "guardrail_events": events, "degraded": True},
    )


def check_agent_opinion(opinion: AgentOpinion) -> GuardrailResult:
    """Validate a single agent opinion."""
    violations: list[GuardrailViolation] = []

    try:
        AgentOpinion.model_validate(opinion.model_dump())
    except Exception as exc:  # noqa: BLE001
        violations.append(
            GuardrailViolation(
                rule="schema",
                severity="block",
                message=f"AgentOpinion schema validation failed: {exc}",
            )
        )

    if not (opinion.claim or "").strip():
        violations.append(
            GuardrailViolation(rule="empty_claim", severity="block", message="Agent claim cannot be empty")
        )

    if opinion.confidence < 0 or opinion.confidence > 1:
        violations.append(
            GuardrailViolation(
                rule="confidence_bounds",
                severity="block",
                message=f"Confidence {opinion.confidence} outside [0, 1]",
            )
        )

    if opinion.risk_theme == RiskTheme.UNKNOWN and opinion.confidence >= 0.7:
        violations.append(
            GuardrailViolation(
                rule="missing_risk_theme",
                severity="block",
                message="High-confidence opinion requires a specific risk_theme",
            )
        )

    blocked = any(v.severity == "block" for v in violations)
    sanitized = _degraded_opinion(opinion, violations) if blocked else opinion
    return GuardrailResult(
        guard_name="agent_output_guard",
        passed=not blocked,
        blocked=blocked,
        violations=violations,
        metadata={"agent_id": opinion.agent_id},
        sanitized_agent_opinion=sanitized,
    )


def guard_agent_opinions(
    opinions: list[AgentOpinion],
    settings: Settings | None = None,
) -> tuple[list[AgentOpinion], list[GuardrailResult]]:
    """Validate all agent opinions; substitute degraded fallback on failure."""
    from aaf.config import Settings as SettingsCls

    cfg = settings or SettingsCls()
    if not cfg.guardrails_enabled:
        return opinions, []

    guarded: list[AgentOpinion] = []
    reports: list[GuardrailResult] = []
    for opinion in opinions:
        report = check_agent_opinion(opinion)
        reports.append(report)
        guarded.append(report.sanitized_agent_opinion or opinion)
    return guarded, reports
