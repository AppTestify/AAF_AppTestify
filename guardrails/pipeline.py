"""Orchestrate guardrails across the governance pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

from aaf.schema import AgentOpinion, EvidenceRecord, UtilityResult
from aaf.schema import ConsensusResult
from guardrails.agent_output_guard import guard_agent_opinions
from guardrails.brief_output_guard import guard_brief_output
from guardrails.evidence_guard import check_evidence
from guardrails.exceptions import GuardrailBlockedError
from guardrails.pm_prompt_guard import check_pm_prompt
from guardrails.tool_scope_guard import validate_agent_tool_plan
from guardrails.types import GuardrailResult

if TYPE_CHECKING:
    from aaf.config import Settings

# Canonical guard order for PipelineResult.guardrails.pipeline_order
PIPELINE_GUARD_ORDER: list[str] = [
    "pm_prompt_guard",
    "evidence_guard",
    "tool_scope_guard",
    "agent_output_guard",
    "brief_output_guard",
]


@dataclass
class InputGuardOutcome:
    prompt: str
    evidence: list[EvidenceRecord]
    reports: list[GuardrailResult] = field(default_factory=list)


@dataclass
class OutputGuardOutcome:
    opinions: list[AgentOpinion]
    explanation: str
    reports: list[GuardrailResult] = field(default_factory=list)


@dataclass
class GuardrailReport:
    """Aggregated guardrail status for a governance run."""

    enabled: bool
    pipeline_order: list[str]
    stages: list[dict[str, Any]]
    all_passed: bool
    any_blocked: bool
    input_blocked: bool
    summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "pipeline_order": self.pipeline_order,
            "stages": self.stages,
            "all_passed": self.all_passed,
            "any_blocked": self.any_blocked,
            "input_blocked": self.input_blocked,
            "summary": self.summary,
        }


def run_pm_prompt_guard(prompt: str, settings: Settings) -> InputGuardOutcome:
    """First input guard — run before connectors/evidence fetch."""
    if not settings.guardrails_enabled:
        return InputGuardOutcome(prompt=prompt.strip(), evidence=[], reports=[])
    report = check_pm_prompt(prompt, settings)
    if report.blocked:
        raise GuardrailBlockedError(report)
    return InputGuardOutcome(prompt=report.sanitized_prompt, evidence=[], reports=[report])


def run_evidence_guard(
    prompt: str,
    evidence: list[EvidenceRecord],
    raw_by_connector: dict[str, dict[str, Any]],
    settings: Settings,
) -> InputGuardOutcome:
    """Evidence guard after normaliser."""
    if not settings.guardrails_enabled:
        return InputGuardOutcome(prompt=prompt, evidence=evidence, reports=[])
    report = check_evidence(evidence, raw_by_connector, settings)
    if report.blocked:
        raise GuardrailBlockedError(report)
    return InputGuardOutcome(
        prompt=prompt,
        evidence=list(report.sanitized_evidence),
        reports=[report],
    )


def run_input_guards(
    prompt: str,
    evidence: list[EvidenceRecord],
    raw_by_connector: dict[str, dict[str, Any]],
    settings: Settings,
    *,
    pm_already_checked: bool = False,
) -> InputGuardOutcome:
    """PM prompt guard (optional) then evidence guard."""
    reports: list[GuardrailResult] = []
    working_prompt = prompt.strip()

    if settings.guardrails_enabled and not pm_already_checked:
        pm_report = check_pm_prompt(prompt, settings)
        reports.append(pm_report)
        if pm_report.blocked:
            raise GuardrailBlockedError(pm_report)
        working_prompt = pm_report.sanitized_prompt
    elif not settings.guardrails_enabled:
        return InputGuardOutcome(prompt=working_prompt, evidence=evidence, reports=reports)

    ev_outcome = run_evidence_guard(working_prompt, evidence, raw_by_connector, settings)
    reports.extend(ev_outcome.reports)
    return InputGuardOutcome(
        prompt=ev_outcome.prompt,
        evidence=ev_outcome.evidence,
        reports=reports,
    )


def run_tool_scope_guards_for_agents(
    agent_tool_plans: dict[str, list[str]],
    settings: Settings,
) -> list[GuardrailResult]:
    """Validate static tool plans per agent before tool execution."""
    if not settings.guardrails_enabled:
        return []
    reports: list[GuardrailResult] = []
    for agent_id, tools in agent_tool_plans.items():
        reports.append(validate_agent_tool_plan(agent_id, tools, settings))
    return reports


def run_output_guards(
    *,
    opinions: list[AgentOpinion],
    explanation: str,
    deterministic_explanation: str,
    utility: UtilityResult,
    consensus: ConsensusResult,
    evidence: list[EvidenceRecord],
    settings: Settings,
) -> OutputGuardOutcome:
    """Agent output guard then brief output guard."""
    reports: list[GuardrailResult] = []
    guarded_ops, agent_reports = guard_agent_opinions(opinions, settings)
    reports.extend(agent_reports)

    final_explanation, brief_report = guard_brief_output(
        explanation,
        deterministic_explanation=deterministic_explanation,
        utility=utility,
        consensus=consensus,
        opinions=guarded_ops,
        evidence=evidence,
        settings=settings,
    )
    reports.append(brief_report)
    return OutputGuardOutcome(opinions=guarded_ops, explanation=final_explanation, reports=reports)


def build_guardrail_report(
    reports: list[GuardrailResult],
    *,
    settings: Optional[Settings] = None,
    extra_stages: Optional[list[GuardrailResult]] = None,
) -> GuardrailReport:
    """Build structured GuardrailReport for PipelineResult."""
    from aaf.config import Settings as SettingsCls

    cfg = settings or SettingsCls()
    all_reports = list(reports) + list(extra_stages or [])
    enabled = cfg.guardrails_enabled

    stages = [
        r.model_dump(
            exclude={"sanitized_evidence", "sanitized_agent_opinion", "sanitized_explanation"}
        )
        for r in all_reports
    ]
    input_guards = {"pm_prompt_guard", "evidence_guard", "budget_cap"}
    input_blocked = any(r.blocked for r in all_reports if r.guard_name in input_guards)
    warned = sum(1 for r in all_reports for v in r.violations if v.severity == "warn")
    blocked_count = sum(1 for r in all_reports if r.blocked)

    return GuardrailReport(
        enabled=enabled,
        pipeline_order=PIPELINE_GUARD_ORDER.copy(),
        stages=stages,
        all_passed=all(r.passed for r in all_reports) if all_reports else True,
        any_blocked=any(r.blocked for r in all_reports),
        input_blocked=input_blocked,
        summary={
            "stage_count": len(all_reports),
            "passed": sum(1 for r in all_reports if r.passed),
            "warned": warned,
            "blocked": blocked_count,
        },
    )


def guardrail_report_dict(
    reports: list[GuardrailResult],
    *,
    settings: Optional[Settings] = None,
    extra_stages: Optional[list[GuardrailResult]] = None,
) -> dict[str, Any]:
    return build_guardrail_report(reports, settings=settings, extra_stages=extra_stages).to_dict()


def apply_agent_output_guards(
    opinions: list[AgentOpinion],
    settings: Settings,
) -> tuple[list[AgentOpinion], list[GuardrailResult]]:
    return guard_agent_opinions(opinions, settings)
