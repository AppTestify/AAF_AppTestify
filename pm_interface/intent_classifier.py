"""Keyword-based PM intent classification for selective agent activation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentCategory(str, Enum):
    RELEASE_READINESS = "release_readiness"
    COST_REVIEW = "cost_review"
    SECURITY_GATE = "security_gate"
    CROSS_DOMAIN = "cross_domain"


_DEFAULT_AGENTS = ["devops", "project_management", "finops"]
_SECURITY_AGENTS = [*_DEFAULT_AGENTS, "devsecops"]

_SECURITY_KEYWORDS = frozenset(
    {
        "cve",
        "cves",
        "secret",
        "secrets",
        "vulnerability",
        "vulnerabilities",
        "policy",
        "compliance",
        "secops",
        "security",
        "devsecops",
        "scan",
        "audit",
        "dependency",
        "dependencies",
    }
)
_COST_KEYWORDS = frozenset({"cost", "spend", "budget", "finops", "cloud cost", "billing", "ri coverage"})
_RELEASE_KEYWORDS = frozenset({"release", "deploy", "ship", "production", "rollback", "ci", "blocker", "sprint"})


@dataclass(frozen=True)
class IntentResult:
    intent: IntentCategory
    agents_needed: list[str]
    connectors: list[str]
    confidence: float


def classify_pm_intent(prompt: str) -> IntentResult:
    """Classify prompt intent using keyword rules (no LLM on Phase 1 path)."""
    text = (prompt or "").lower()
    tokens = set(text.replace(",", " ").replace(".", " ").split())

    security_hits = sum(1 for kw in _SECURITY_KEYWORDS if kw in text or kw in tokens)
    cost_hits = sum(1 for kw in _COST_KEYWORDS if kw in text)
    release_hits = sum(1 for kw in _RELEASE_KEYWORDS if kw in text)

    if security_hits >= 2 or (security_hits >= 1 and "security" in text):
        intent = IntentCategory.SECURITY_GATE
        agents = list(_SECURITY_AGENTS)
        connectors = ["github", "jira", "finops"]
        confidence = min(0.95, 0.55 + security_hits * 0.1)
    elif cost_hits >= 2 and release_hits == 0:
        intent = IntentCategory.COST_REVIEW
        agents = list(_DEFAULT_AGENTS)
        connectors = ["finops", "jira", "github"]
        confidence = min(0.9, 0.5 + cost_hits * 0.1)
    elif release_hits >= 1 and security_hits == 0:
        intent = IntentCategory.RELEASE_READINESS
        agents = list(_DEFAULT_AGENTS)
        connectors = ["github", "jira", "finops"]
        confidence = min(0.9, 0.5 + release_hits * 0.08)
    elif security_hits >= 1 and (release_hits >= 1 or cost_hits >= 1):
        intent = IntentCategory.CROSS_DOMAIN
        agents = list(_SECURITY_AGENTS)
        connectors = ["github", "jira", "finops"]
        confidence = 0.75
    else:
        intent = IntentCategory.RELEASE_READINESS
        agents = list(_DEFAULT_AGENTS)
        connectors = ["github", "jira", "finops"]
        confidence = 0.45

    return IntentResult(intent=intent, agents_needed=agents, connectors=connectors, confidence=confidence)
