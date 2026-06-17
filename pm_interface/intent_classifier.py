from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentCategory(str, Enum):
    RELEASE_READINESS = "release_readiness"
    DELIVERY_HEALTH = "delivery_health"
    COST_ANOMALY = "cost_anomaly"
    COST_REVIEW = "cost_review"
    SECURITY_GATE = "security_gate"
    CROSS_DOMAIN = "cross_domain"

_SECURITY_KEYWORDS = frozenset({"cve", "secret", "vulnerability", "security", "scan"})
_COST_KEYWORDS = frozenset({"cost", "spend", "budget", "finops", "anomaly"})
_DELIVERY_HEALTH_KEYWORDS = frozenset({"latency", "error", "health", "observability", "blocker", "sprint", "delivery", "incident", "mttr", "reliability", "sla", "uptime", "downtime"})
_RELEASE_KEYWORDS = frozenset({"release", "deploy", "ship", "today", "monday"})

def classify_intent(prompt: str) -> tuple[IntentCategory, list[str]]:
    """Classify intent returning tuple of (IntentCategory, agents_needed) in <1ms."""
    text = (prompt or "").lower()
    
    if any(kw in text for kw in _SECURITY_KEYWORDS):
        return IntentCategory.SECURITY_GATE, ["devops", "project_management", "finops", "devsecops"]
    elif any(kw in text for kw in _COST_KEYWORDS):
        return IntentCategory.COST_ANOMALY, ["devops", "project_management", "finops"]
    elif any(kw in text for kw in _DELIVERY_HEALTH_KEYWORDS):
        return IntentCategory.DELIVERY_HEALTH, ["project_management", "devops"]
    elif any(kw in text for kw in _RELEASE_KEYWORDS):
        return IntentCategory.RELEASE_READINESS, ["devops", "project_management", "finops"]
        
    return IntentCategory.RELEASE_READINESS, ["devops", "project_management", "finops"]

@dataclass(frozen=True)
class IntentResult:
    intent: IntentCategory
    agents_needed: list[str]
    connectors: list[str]
    confidence: float

def classify_pm_intent(prompt: str) -> IntentResult:
    intent, agents = classify_intent(prompt)
    return IntentResult(
        intent=intent,
        agents_needed=agents,
        connectors=["github", "jira", "finops", "pagerduty"],
        confidence=0.85
    )
