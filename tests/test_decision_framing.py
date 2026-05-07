"""Decision framing and pipeline settings overrides."""

from __future__ import annotations

from types import SimpleNamespace

from aaf.config import Settings
from app.services.config_resolver import apply_pipeline_overrides
from app.services.decision_framing import build_decision_framing, orchestration_snapshot_from_run_payload


def test_orchestration_snapshot_from_pipeline_json():
    out = {
        "consensus": {"consensus_score": 0.72},
        "rar": {
            "rar_triggered": True,
            "rar_loops": 1,
            "consensus_before": 0.4,
            "consensus_after": 0.72,
        },
        "utility": {"recommended_action": "observe", "utility_score": 0.61},
        "explainability": {"xi_score": 0.55},
        "pm_view": {"detail_json": {}},
    }
    snap = orchestration_snapshot_from_run_payload(out)
    assert snap["consensus_score"] == 0.72
    assert snap["rar_triggered"] is True
    assert snap["recommended_action"] == "observe"


def test_build_decision_framing_with_agentic():
    out = {
        "consensus": {"consensus_score": 0.8},
        "rar": {"rar_triggered": False, "rar_loops": 0, "consensus_before": 0.8, "consensus_after": 0.8},
        "utility": {"recommended_action": "mitigate_monitor", "utility_score": 0.5},
        "explainability": {"xi_score": 0.7},
        "pm_view": {"detail_json": {}},
        "agentic_intelligence": {
            "consensus": {"consensus_score": 0.65, "conflict_detected": False, "confidence": 0.7},
        },
    }
    df = build_decision_framing(out)
    assert df["primary_recommendation_source"] == "orchestration"
    assert df["orchestration"]["consensus_score"] == 0.8
    assert df["findings_synthesis"]["consensus_score"] == 0.65


def test_apply_pipeline_overrides_from_ui_preferences():
    base = Settings()
    ts = SimpleNamespace(ui_preferences={"governance_pipeline": {"tau_consensus": 0.61, "w_perf": 0.5}})
    merged = apply_pipeline_overrides(base, ts)
    assert merged.tau_consensus == 0.61
    assert merged.w_perf == 0.5
    assert merged.w_cost == base.w_cost
