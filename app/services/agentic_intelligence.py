"""Multi-agent intelligence synthesis aligned with pipeline agents."""

from __future__ import annotations

import json
from typing import Any

from aaf.schema import AgentOpinion, RiskTheme
from app.services.llm_runtime import ActiveProvider, LLMInvocationError, invoke_json_with_failover
from orchestrator.consensus import compute_consensus as _pipeline_compute_consensus


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, round(v, 4)))


def _severity_from_confidence(confidence: float, risk_theme: str) -> str:
    if confidence >= 0.75 or risk_theme == RiskTheme.SECURITY_RISK.value:
        return "critical"
    if confidence >= 0.45:
        return "warning"
    return "info"


def opinions_to_findings(opinions: list[AgentOpinion]) -> list[dict[str, Any]]:
    """Convert pipeline AgentOpinion list to intelligence dashboard findings."""
    name_map = {
        "devops": ("DevOpsAgent", "deployment"),
        "finops": ("FinOpsAgent", "cost"),
        "devsecops": ("DevSecOpsAgent", "security"),
        "project_management": ("PMAgent", "delivery"),
    }
    findings: list[dict[str, Any]] = []
    for op in opinions:
        agent_name, domain = name_map.get(op.agent_id, (f"{op.agent_id.title()}Agent", "governance"))
        findings.append(
            {
                "agent_name": agent_name,
                "domain": domain,
                "severity": _severity_from_confidence(op.confidence, op.risk_theme.value),
                "confidence": _clamp(op.confidence),
                "summary": op.claim,
                "evidence_json": {
                    "evidence": op.evidence,
                    "raw_signals": op.raw_signals,
                    "risk_theme": op.risk_theme.value,
                },
            }
        )
    return findings


def build_agent_findings(integration_signals: dict[str, Any], obs: dict[str, Any]) -> list[dict[str, Any]]:
    """Build heuristic findings from integration telemetry (fallback path)."""
    findings: list[dict[str, Any]] = []
    github = integration_signals.get("github") or {}
    aws = integration_signals.get("aws") or {}
    azure = integration_signals.get("azure") or {}
    jira = integration_signals.get("jira") or {}

    devops_conf = _clamp(1.0 - float(github.get("failing_checks", 0)) / 5.0)
    findings.append(
        {
            "agent_name": "DevOpsAgent",
            "domain": "deployment",
            "severity": "warning" if github.get("failing_checks", 0) else "info",
            "confidence": devops_conf,
            "summary": f"CI/CD checks failing: {github.get('failing_checks', 0)}; active runs: {github.get('active_runs', 0)}",
            "evidence_json": {"github": github},
        }
    )

    blocked = int(jira.get("blocked_tickets", 0) or 0)
    pm_conf = _clamp(0.4 + blocked * 0.12) if blocked else 0.15
    findings.append(
        {
            "agent_name": "PMAgent",
            "domain": "delivery",
            "severity": "critical" if blocked >= 5 else "warning" if blocked else "info",
            "confidence": pm_conf,
            "summary": f"Sprint blockers: {blocked}; flow efficiency: {jira.get('flow_efficiency', 'n/a')}",
            "evidence_json": {"jira": jira},
        }
    )

    cost_signal = str(aws.get("cost_trend") or azure.get("cost_trend") or "stable")
    finops_conf = _clamp(0.55 if "up" in cost_signal else 0.25)
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
    devsecops_conf = _clamp(min(1.0, security_findings / 4.0 + 0.1))
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


def build_agent_findings_with_llm(
    integration_signals: dict[str, Any],
    obs: dict[str, Any],
    providers: list[ActiveProvider],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    baseline = build_agent_findings(integration_signals, obs)
    if not providers:
        return baseline, {"status": "degraded", "reason": "no_active_provider"}
    prompt = (
        "Generate JSON with key 'findings' as an array of 3-6 objects. "
        "Each object must contain: agent_name, domain, severity(info|warning|critical), confidence(0..1), summary, evidence_json. "
        "Include DevOpsAgent, PMAgent, FinOpsAgent, and DevSecOpsAgent. "
        "Use this context:\n"
        + json.dumps({"integration_signals": integration_signals, "observability": obs}, default=str)
    )
    try:
        payload, meta = invoke_json_with_failover(providers, prompt)
        findings = payload.get("findings")
        if not isinstance(findings, list) or not findings:
            raise LLMInvocationError("missing findings array")
        normalized: list[dict[str, Any]] = []
        for row in findings:
            if not isinstance(row, dict):
                continue
            normalized.append(
                {
                    "agent_name": str(row.get("agent_name") or "LLMAgent"),
                    "domain": str(row.get("domain") or "governance"),
                    "severity": str(row.get("severity") or "warning"),
                    "confidence": _clamp(float(row.get("confidence") or 0.5)),
                    "summary": str(row.get("summary") or "LLM-generated governance finding"),
                    "evidence_json": row.get("evidence_json") if isinstance(row.get("evidence_json"), dict) else {},
                }
            )
        if not normalized:
            raise LLMInvocationError("no valid findings")
        return normalized, {"status": "ok", **meta}
    except Exception as exc:  # noqa: BLE001
        return baseline, {
            "status": "degraded",
            "providers_attempted": [p.provider_name for p in providers],
            "reason": str(exc),
        }


def compute_consensus_from_findings(findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Unify with pipeline consensus via shared theme-weighted algorithm when possible."""
    if not findings:
        return {"consensus_score": 0.0, "conflict_detected": False, "confidence": 0.0}

    opinions: list[AgentOpinion] = []
    theme_map = {
        "deployment": RiskTheme.OPERATIONAL_RISK,
        "delivery": RiskTheme.DELIVERY_RISK,
        "cost": RiskTheme.COST_RISK,
        "security": RiskTheme.SECURITY_RISK,
        "reliability": RiskTheme.RELIABILITY_RISK,
    }
    for f in findings:
        domain = str(f.get("domain", "governance"))
        opinions.append(
            AgentOpinion(
                agent_id=str(f.get("agent_name", "agent")).lower().replace("agent", ""),
                claim=str(f.get("summary", "")),
                confidence=float(f.get("confidence", 0.0) or 0.0),
                risk_theme=theme_map.get(domain, RiskTheme.UNKNOWN),
            )
        )
    result = _pipeline_compute_consensus(opinions)
    severities = {str(f.get("severity", "info")) for f in findings}
    conflict = "critical" in severities and "info" in severities
    return {
        "consensus_score": result.consensus_score,
        "conflict_detected": conflict,
        "confidence": _clamp(result.consensus_score * (0.75 if conflict else 1.0)),
    }


# Backward-compatible alias
compute_consensus = compute_consensus_from_findings


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
