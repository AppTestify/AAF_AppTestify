"""Orchestrate guardrails across the governance pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aaf.schema import AgentOpinion, EvidenceRecord
from guardrails.agent_output_guard import guard_agent_opinions
from guardrails.evidence_guard import check_evidence
from guardrails.exceptions import GuardrailBlockedError
from guardrails.pm_prompt_guard import check_pm_prompt
from guardrails.types import GuardrailResult

if TYPE_CHECKING:
    from aaf.config import Settings


@dataclass
class InputGuardOutcome:
    prompt: str
    evidence: list[EvidenceRecord]
    reports: list[GuardrailResult] = field(default_factory=list)


def run_input_guards(
    prompt: str,
    evidence: list[EvidenceRecord],
    raw_by_connector: dict[str, dict[str, Any]],
    settings: Settings,
) -> InputGuardOutcome:
    """PM prompt guard then evidence guard."""
    reports: list[GuardrailResult] = []
    if not settings.guardrails_enabled:
        return InputGuardOutcome(prompt=prompt, evidence=evidence, reports=reports)

    pm_report = check_pm_prompt(prompt, settings)
    reports.append(pm_report)
    if pm_report.blocked:
        raise GuardrailBlockedError(pm_report)

    ev_report = check_evidence(evidence, raw_by_connector, settings)
    reports.append(ev_report)
    if ev_report.blocked:
        raise GuardrailBlockedError(ev_report)

    return InputGuardOutcome(
        prompt=pm_report.sanitized_prompt,
        evidence=list(ev_report.sanitized_evidence),
        reports=reports,
    )


def guardrail_report_dict(reports: list[GuardrailResult]) -> dict[str, Any]:
    return {
        "stages": [
            r.model_dump(
                exclude={"sanitized_evidence", "sanitized_agent_opinion", "sanitized_explanation"}
            )
            for r in reports
        ],
        "all_passed": all(r.passed for r in reports),
        "any_blocked": any(r.blocked for r in reports),
    }


def apply_agent_output_guards(
    opinions: list[AgentOpinion],
    settings: Settings,
) -> tuple[list[AgentOpinion], list[GuardrailResult]]:
    return guard_agent_opinions(opinions, settings)
