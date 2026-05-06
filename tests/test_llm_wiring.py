from __future__ import annotations

from app.services.agentic_intelligence import build_agent_findings_with_llm


def test_findings_llm_soft_fallback_without_provider():
    findings, meta = build_agent_findings_with_llm({"github": {}}, {"latency_ms_p95": 10, "error_rate": 0.0}, None)
    assert len(findings) >= 1
    assert meta["status"] == "degraded"
    assert meta["reason"] == "no_active_provider"
