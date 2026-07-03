"""Sync vs async governance run payload shape parity."""

from __future__ import annotations

from pm_interface.decision_formatter import build_governance_brief, pipeline_result_to_jsonable
from app.services.decision_framing import build_decision_framing
from app.services.run_payload import enrich_run_payload


def _minimal_out() -> dict:
    return {
        "prompt": "release check",
        "agent_opinions": [{"agent_id": "devops", "claim": "ok", "confidence": 0.5, "evidence_refs": [], "evidence": [], "risk_theme": "low_risk", "raw_signals": {}}],
        "consensus": {"consensus_score": 0.6, "theme_counts": {}, "notes": ""},
        "rar": {"rar_triggered": False, "rar_loops": 0, "consensus_before": 0.6, "consensus_after": 0.6, "reground_notes": []},
        "utility": {"recommended_action": "observe", "utility_score": 0.5, "global_utility": 0.5, "perf_index": 0.5, "cost_index": 0.5, "risk_index": 0.5, "scores_by_action": {}, "weights_used": {}},
        "explainability": {"xi_score": 0.5, "checks": {}},
        "explanation": "Test explanation",
        "pm_view": {"title": "Recommended: Observe", "summary_markdown": "Summary", "detail_json": {}},
        "guardrails": {"enabled": True, "pipeline_order": [], "stages": [], "all_passed": True, "summary": {"stage_count": 0, "passed": 0, "warned": 0, "blocked": 0}},
        "llm_cost": {"totals": {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "call_count": 0}, "by_phase": {}, "by_agent": {}, "calls": []},
        "intent": {"category": "release_readiness", "agents_needed": ["devops", "project_management", "finops"]},
        "agents_activated": ["devops", "project_management", "finops"],
    }


def test_enrich_adds_canonical_fields():
    out = _minimal_out()
    enriched = enrich_run_payload(out, db=None, tenant=None, settings=None, ts_row=None)  # type: ignore[arg-type]
    assert "decision_framing" in enriched
    assert "governance_brief" in enriched
    assert enriched["agent_outputs"] == enriched["agent_opinions"]
    assert enriched["decision_framing"]["intent_category"] == "release_readiness"


def test_build_governance_brief_matches_pipeline_fields():
    out = _minimal_out()
    brief = build_governance_brief(out)
    assert brief["markdown"] == out["explanation"]
    assert brief["audit_detail"]["guardrails"] == out["guardrails"]
    assert brief["audit_detail"]["llm_cost"] == out["llm_cost"]


def test_decision_framing_orchestration_has_indices():
    out = _minimal_out()
    df = build_decision_framing(out)
    assert df["orchestration"]["perf_index"] == 0.5
    assert df["orchestration"]["global_utility"] == 0.5
