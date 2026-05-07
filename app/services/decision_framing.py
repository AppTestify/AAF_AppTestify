"""Stable decision framing for orchestration vs findings synthesis (API + audit)."""

from __future__ import annotations

from typing import Any


def orchestration_snapshot_from_run_payload(out: dict[str, Any]) -> dict[str, Any]:
    """Extract orchestration scores from pipeline JSON (pipeline_result_to_jsonable shape)."""
    consensus = out.get("consensus") if isinstance(out.get("consensus"), dict) else {}
    rar = out.get("rar") if isinstance(out.get("rar"), dict) else {}
    utility = out.get("utility") if isinstance(out.get("utility"), dict) else {}
    explain = out.get("explainability") if isinstance(out.get("explainability"), dict) else {}
    pm = out.get("pm_view") if isinstance(out.get("pm_view"), dict) else {}
    detail = pm.get("detail_json") if isinstance(pm.get("detail_json"), dict) else {}

    rec_action = utility.get("recommended_action")
    if rec_action is None and isinstance(detail.get("recommended_action"), str):
        rec_action = detail["recommended_action"]

    return {
        "consensus_score": consensus.get("consensus_score"),
        "rar_triggered": rar.get("rar_triggered"),
        "rar_loops": rar.get("rar_loops"),
        "consensus_before": rar.get("consensus_before"),
        "consensus_after": rar.get("consensus_after"),
        "recommended_action": rec_action,
        "utility_score": utility.get("utility_score"),
        "xi_score": explain.get("xi_score"),
    }


def build_decision_framing(out: dict[str, Any]) -> dict[str, Any]:
    """
    Single place for PM/exec semantics: orchestration path vs findings synthesis.

    Expects `out` after pipeline_result_to_jsonable and optional agentic_intelligence block.
    """
    orch = orchestration_snapshot_from_run_payload(out)

    findings_block = out.get("agentic_intelligence")
    findings_consensus: dict[str, Any] = {}
    if isinstance(findings_block, dict):
        fc = findings_block.get("consensus")
        if isinstance(fc, dict):
            findings_consensus = {
                "consensus_score": fc.get("consensus_score"),
                "conflict_detected": fc.get("conflict_detected"),
                "confidence": fc.get("confidence"),
            }

    return {
        "primary_recommendation_source": "orchestration",
        "orchestration": orch,
        "findings_synthesis": findings_consensus,
    }
