"""Brief output guardrail — hallucination checks and action lock."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from aaf.schema import AgentOpinion, ConsensusResult, EvidenceRecord, GovernanceAction, UtilityResult
from guardrails.types import GuardrailResult, GuardrailViolation

if TYPE_CHECKING:
    from aaf.config import Settings

_ACTION_KEYWORDS: dict[GovernanceAction, list[str]] = {
    GovernanceAction.ROLLBACK: ["rollback", "roll back", "revert", "roll-back"],
    GovernanceAction.MITIGATE_MONITOR: ["mitigate", "mitigation", "monitor closely"],
    GovernanceAction.SCALE_ADJUST: ["scale up", "scale down", "capacity adjustment", "autoscale"],
    GovernanceAction.PATCH_BLOCK_RELEASE: ["block release", "patch", "do not release"],
    GovernanceAction.HOLD_RELEASE: ["hold release", "hold the release", "do not release", "delay release"],
    GovernanceAction.OBSERVE: ["observe", "no immediate action", "watch", "continue monitoring"],
}

_ACTION_LABELS: dict[GovernanceAction, str] = {
    GovernanceAction.ROLLBACK: "Rollback to stable deployment",
    GovernanceAction.MITIGATE_MONITOR: "Mitigate and monitor",
    GovernanceAction.SCALE_ADJUST: "Scale / capacity adjustment",
    GovernanceAction.PATCH_BLOCK_RELEASE: "Patch or block release",
    GovernanceAction.HOLD_RELEASE: "Hold release",
    GovernanceAction.OBSERVE: "No immediate action / observe",
}


def _detect_conflicting_action(text: str, recommended: GovernanceAction) -> Optional[GovernanceAction]:
    lower = text.lower()
    for action, keywords in _ACTION_KEYWORDS.items():
        if action == recommended:
            continue
        if any(kw in lower for kw in keywords):
            return action
    return None


def _consensus_cited_incorrectly(text: str, consensus_score: float) -> bool:
    for match in re.finditer(r"consensus[^\d]{0,20}(\d+(?:\.\d+)?)", text.lower()):
        try:
            cited = float(match.group(1))
        except ValueError:
            continue
        if cited > 1.0:
            cited = cited / 100.0
        if abs(cited - consensus_score) > 0.2:
            return True
    return False


def _novel_numeric_claim(text: str, allowed_corpus: str) -> bool:
    """Flag round numbers in the brief that do not appear in structured context."""
    allowed = allowed_corpus.lower()
    for match in re.finditer(r"\b(\d{2,})\b", text):
        token = match.group(1)
        if token in allowed:
            continue
        # Ignore years and common section numbers
        if len(token) == 4 and token.startswith(("19", "20")):
            continue
        return True
    return False


def check_brief_output(
    explanation: str,
    *,
    deterministic_explanation: str,
    utility: UtilityResult,
    consensus: ConsensusResult,
    opinions: list[AgentOpinion],
    evidence: list[EvidenceRecord],
    settings: Optional[Settings] = None,
) -> GuardrailResult:
    """Validate LLM governance brief; fall back to deterministic explanation on failure."""
    from aaf.config import Settings as SettingsCls

    cfg = settings or SettingsCls()
    violations: list[GuardrailViolation] = []
    recommended = utility.recommended_action
    label = _ACTION_LABELS.get(recommended, recommended.value)

    if not cfg.guardrails_enabled:
        return GuardrailResult(
            guard_name="brief_output_guard",
            passed=True,
            violations=[],
            metadata={"action_lock": "skipped"},
            sanitized_explanation=explanation,
        )

    conflicting = _detect_conflicting_action(explanation, recommended)
    if conflicting is not None:
        violations.append(
            GuardrailViolation(
                rule="action_lock",
                severity="block",
                message=(
                    f"Brief mentions conflicting action '{conflicting.value}' "
                    f"but orchestrator recommended '{recommended.value}'"
                ),
            )
        )

    recommended_present = (
        recommended.value.replace("_", " ") in explanation.lower()
        or label.lower() in explanation.lower()
        or any(kw in explanation.lower() for kw in _ACTION_KEYWORDS.get(recommended, []))
    )
    if not recommended_present and conflicting is None:
        violations.append(
            GuardrailViolation(
                rule="action_lock",
                severity="block",
                message=f"Brief does not reflect orchestrator action '{recommended.value}'",
            )
        )

    if _consensus_cited_incorrectly(explanation, consensus.consensus_score):
        violations.append(
            GuardrailViolation(
                rule="hallucination_consensus",
                severity="block",
                message="Brief cites a consensus score that diverges from orchestrator output",
            )
        )

    corpus = " ".join(
        [
            label,
            recommended.value,
            str(consensus.consensus_score),
            " ".join(o.claim for o in opinions),
            " ".join(e.summary for e in evidence),
        ]
    )
    if _novel_numeric_claim(explanation, corpus):
        violations.append(
            GuardrailViolation(
                rule="hallucination_evidence",
                severity="block",
                message="Brief contains numeric claims not grounded in evidence or agent opinions",
            )
        )

    action_violations = [v for v in violations if v.severity == "block"]
    use_fallback = len(action_violations) > 0
    sanitized = deterministic_explanation if use_fallback else explanation
    return GuardrailResult(
        guard_name="brief_output_guard",
        passed=True,
        blocked=False,
        violations=violations,
        sanitized_explanation=sanitized,
        metadata={
            "action_lock": "enforced" if use_fallback else "ok",
            "fallback": "deterministic" if use_fallback else "llm",
            "recommended_action": recommended.value,
        },
    )


def guard_brief_output(
    explanation: str,
    *,
    deterministic_explanation: str,
    utility: UtilityResult,
    consensus: ConsensusResult,
    opinions: list[AgentOpinion],
    evidence: list[EvidenceRecord],
    settings: Optional[Settings] = None,
) -> tuple[str, GuardrailResult]:
    """Return sanitized explanation and guard report."""
    report = check_brief_output(
        explanation,
        deterministic_explanation=deterministic_explanation,
        utility=utility,
        consensus=consensus,
        opinions=opinions,
        evidence=evidence,
        settings=settings,
    )
    text = report.sanitized_explanation or explanation
    return text, report
