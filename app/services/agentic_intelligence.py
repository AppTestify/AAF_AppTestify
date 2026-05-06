"""Multi-agent intelligence synthesis and consensus scoring."""

from __future__ import annotations

from typing import Any


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, round(v, 4)))


def build_agent_findings(integration_signals: dict[str, Any], obs: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    github = integration_signals.get("github") or {}
    aws = integration_signals.get("aws") or {}
    azure = integration_signals.get("azure") or {}

    devops_conf = 1.0 - _clamp(float(github.get("failing_checks", 0)) / 5.0)
    findings.append(
        {
            "agent_name": "DevOpsAgent",
            "domain": "deployment",
            "severity": "warning" if github.get("failing_checks", 0) else "info",
            "confidence": _clamp(devops_conf),
            "summary": f"CI/CD checks failing: {github.get('failing_checks', 0)}; active runs: {github.get('active_runs', 0)}",
            "evidence_json": {"github": github},
        }
    )

    latency = float(obs.get("latency_ms_p95", 0.0) or 0.0)
    err_rate = float(obs.get("error_rate", 0.0) or 0.0)
    sre_conf = _clamp(1.0 - min(1.0, (latency / 1200.0) + (err_rate * 2.0)))
    findings.append(
        {
            "agent_name": "SREAgent",
            "domain": "reliability",
            "severity": "critical" if latency > 900 or err_rate > 0.08 else "warning" if latency > 500 else "info",
            "confidence": sre_conf,
            "summary": f"Latency p95={latency:.0f}ms, error_rate={err_rate:.3f}, queue_depth={obs.get('run_queue_depth', 0)}",
            "evidence_json": {"observability": obs},
        }
    )

    cost_signal = str(aws.get("cost_trend") or azure.get("cost_trend") or "stable")
    finops_conf = _clamp(0.55 if "up" in cost_signal else 0.8)
    findings.append(
        {
            "agent_name": "FinOpsAgent",
            "domain": "cost",
            "severity": "warning" if "up" in cost_signal else "info",
            "confidence": finops_conf,
            "summary": f"Cost trend detected: {cost_signal}",
            "evidence_json": {"aws": aws, "azure": azure},
        }
    )

    security_findings = int(aws.get("security_findings", 0) or 0) + int(azure.get("policy_violations", 0) or 0)
    devsecops_conf = _clamp(1.0 - min(1.0, security_findings / 6.0))
    findings.append(
        {
            "agent_name": "DevSecOpsAgent",
            "domain": "security",
            "severity": "critical" if security_findings >= 4 else "warning" if security_findings else "info",
            "confidence": devsecops_conf,
            "summary": f"Security/policy findings detected: {security_findings}",
            "evidence_json": {"aws": aws, "azure": azure},
        }
    )

    return findings


def compute_consensus(findings: list[dict[str, Any]]) -> dict[str, Any]:
    if not findings:
        return {"consensus_score": 0.0, "conflict_detected": False, "confidence": 0.0}
    confidences = [float(f.get("confidence", 0.0) or 0.0) for f in findings]
    severities = {str(f.get("severity", "info")) for f in findings}
    consensus = _clamp(sum(confidences) / len(confidences))
    conflict = "critical" in severities and "info" in severities
    confidence = _clamp(consensus * (0.75 if conflict else 1.0))
    return {"consensus_score": consensus, "conflict_detected": conflict, "confidence": confidence}


def build_incident(findings: list[dict[str, Any]], consensus: dict[str, Any]) -> dict[str, Any]:
    severity_order = {"info": 0, "warning": 1, "critical": 2}
    top = max(findings, key=lambda f: severity_order.get(str(f.get("severity", "info")), 0))
    title = f"{top.get('domain', 'ops').title()} anomaly requires governance attention"
    recommendation = {
        "recommended_action": "hold_release" if top.get("severity") == "critical" else "investigate_and_monitor",
        "rationale": top.get("summary"),
    }
    return {
        "title": title,
        "severity": top.get("severity", "warning"),
        "status": "open",
        "confidence": consensus["confidence"],
        "consensus_score": consensus["consensus_score"],
        "conflict_detected": consensus["conflict_detected"],
        "evidence_json": {"findings": findings},
        "recommendation_json": recommendation,
    }


def build_executive_summary(incident: dict[str, Any]) -> dict[str, Any]:
    severity = str(incident.get("severity", "warning"))
    consensus = float(incident.get("consensus_score", 0.0))
    confidence = float(incident.get("confidence", 0.0))
    rec = incident.get("recommendation_json", {})
    content = (
        f"Operational governance detected a {severity} incident. "
        f"Cross-agent consensus is {consensus:.2f} with confidence {confidence:.2f}. "
        f"Recommended action: {rec.get('recommended_action', 'review')}. "
        f"Rationale: {rec.get('rationale', 'n/a')}."
    )
    xi = _clamp((consensus + confidence) / 2.0)
    return {
        "summary_type": "incident",
        "title": "Executive Incident Brief",
        "content": content,
        "xi_score": xi,
        "metadata_json": {"severity": severity, "consensus_score": consensus, "confidence": confidence},
    }
