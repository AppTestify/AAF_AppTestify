from __future__ import annotations

from aaf.config import Settings
from aaf.schema import AgentOpinion, ConsensusResult, EvidenceRecord, GovernanceAction, RiskTheme, UtilityResult
from guardrails.brief_output_guard import guard_brief_output
from llm.deterministic_explainer import build_explanation


def _context():
    opinions = [
        AgentOpinion(
            agent_id="devops",
            claim="CI failures detected.",
            confidence=0.8,
            risk_theme=RiskTheme.OPERATIONAL_RISK,
        )
    ]
    consensus = ConsensusResult(consensus_score=0.62, dominant_theme=RiskTheme.OPERATIONAL_RISK)
    utility = UtilityResult(
        recommended_action=GovernanceAction.MITIGATE_MONITOR,
        utility_score=0.71,
        scores_by_action={"mitigate_monitor": 0.71},
    )
    evidence = [EvidenceRecord(source="github", kind="workflow_run", summary="CI failed", severity=0.8)]
    deterministic = build_explanation(
        prompt="Should we release?",
        opinions=opinions,
        consensus=consensus,
        rar=__import__("aaf.schema", fromlist=["RARResult"]).RARResult(
            rar_triggered=False,
            rar_loops=0,
            consensus_before=0.62,
            consensus_after=0.62,
        ),
        utility=utility,
    )
    return opinions, consensus, utility, evidence, deterministic


def test_passes_aligned_llm_brief():
    opinions, consensus, utility, evidence, deterministic = _context()
    llm_text = (
        "## Recommended action\n"
        "- **Mitigate and monitor** given CI failures and consensus 0.62.\n"
    )
    text, report = guard_brief_output(
        llm_text,
        deterministic_explanation=deterministic,
        utility=utility,
        consensus=consensus,
        opinions=opinions,
        evidence=evidence,
        settings=Settings(),
    )
    assert report.passed
    assert "Mitigate" in text


def test_falls_back_on_conflicting_action():
    opinions, consensus, utility, evidence, deterministic = _context()
    llm_text = "Immediate rollback is required before any release proceeds."
    text, report = guard_brief_output(
        llm_text,
        deterministic_explanation=deterministic,
        utility=utility,
        consensus=consensus,
        opinions=opinions,
        evidence=evidence,
        settings=Settings(),
    )
    assert report.passed
    assert report.metadata.get("fallback") == "deterministic"
    assert text == deterministic
    assert any(v.rule == "action_lock" for v in report.violations)


def test_falls_back_on_wrong_consensus_citation():
    opinions, consensus, utility, evidence, deterministic = _context()
    llm_text = "Consensus score 0.95 supports mitigate and monitor."
    text, report = guard_brief_output(
        llm_text,
        deterministic_explanation=deterministic,
        utility=utility,
        consensus=consensus,
        opinions=opinions,
        evidence=evidence,
        settings=Settings(),
    )
    assert report.passed
    assert report.metadata.get("fallback") == "deterministic"
    assert text == deterministic
