"""RAR and governance workflow orchestration utilities."""

from __future__ import annotations

from typing import Any


def run_rar_iteration(incident: dict[str, Any], telemetry: dict[str, Any]) -> dict[str, Any]:
    before = float(incident.get("confidence", 0.0) or 0.0)
    queue_depth = float(telemetry.get("run_queue_depth", 0.0) or 0.0)
    error_rate = float(telemetry.get("error_rate", 0.0) or 0.0)
    enrichment = {
        "telemetry_window_seconds": telemetry.get("window_seconds", 0),
        "queue_depth": queue_depth,
        "error_rate": error_rate,
        "top_endpoints": telemetry.get("endpoints_top", [])[:5],
    }
    gain = 0.18 if before < 0.45 else 0.08 if before < 0.7 else 0.03
    penalty = min(0.07, (error_rate * 0.2) + (queue_depth / 1000.0))
    after = max(0.0, min(1.0, round(before + gain - penalty, 4)))
    return {
        "trigger_reason": "low_confidence" if before < 0.7 else "manual_review",
        "confidence_before": before,
        "confidence_after": after,
        "evidence_enrichment_json": enrichment,
    }


def evaluate_workflow(workflow_type: str, incident: dict[str, Any], telemetry: dict[str, Any]) -> dict[str, Any]:
    wf = workflow_type.strip().lower()
    severity = str(incident.get("severity", "warning"))
    confidence = float(incident.get("confidence", 0.0) or 0.0)
    consensus = float(incident.get("consensus_score", 0.0) or 0.0)
    error_rate = float(telemetry.get("error_rate", 0.0) or 0.0)
    latency = float(telemetry.get("latency_ms_p95", 0.0) or 0.0)

    if wf == "cost_spike":
        score = round(min(1.0, (0.6 - confidence) + (0.4 if severity == "critical" else 0.15)), 4)
        decision = "investigate_now" if score >= 0.5 else "monitor"
        summary = f"Cost spike workflow score={score:.2f}; decision={decision}."
    elif wf == "security_governance":
        score = round(min(1.0, (0.5 if severity == "critical" else 0.25) + (1 - confidence) * 0.5), 4)
        decision = "block_release" if score >= 0.55 else "guardrail_release"
        summary = f"Security governance score={score:.2f}; decision={decision}."
    elif wf == "post_incident_review":
        score = round(min(1.0, (0.5 * (1 - consensus)) + (0.5 if error_rate > 0.05 else 0.2)), 4)
        decision = "generate_postmortem"
        summary = f"Post-incident review score={score:.2f}; decision={decision}."
    else:
        score = round(min(1.0, (latency / 1000.0) * 0.5 + (error_rate * 3.0) * 0.5), 4)
        decision = "review"
        summary = f"Workflow '{wf}' evaluated with score={score:.2f}; decision={decision}."

    return {
        "workflow_type": wf,
        "status": "completed",
        "decision": decision,
        "score": score,
        "summary": summary,
        "output_json": {
            "incident": incident,
            "telemetry": {
                "error_rate": error_rate,
                "latency_ms_p95": latency,
                "run_queue_depth": telemetry.get("run_queue_depth", 0),
            },
        },
    }
