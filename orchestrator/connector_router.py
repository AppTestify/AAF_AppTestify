"""Semantic connector routing with confidence fallback."""

from __future__ import annotations

import re

from pm_interface.router import route_connectors as keyword_route

_CONNECTOR_VECTORS: dict[str, set[str]] = {
    "github": {"github", "pull", "request", "workflow", "ci", "cd", "build", "commit", "release", "merge", "repo"},
    "jira": {"jira", "sprint", "ticket", "story", "epic", "blocked", "backlog", "defect", "delivery"},
    "finops": {"cost", "finops", "budget", "spend", "cloud", "bill", "aws", "azure", "gcp", "capacity", "scale"},
    "gitlab": {"gitlab", "merge", "request", "pipeline"},
    "bitbucket": {"bitbucket", "pipeline"},
    "pagerduty": {"pagerduty", "opsgenie", "incident", "oncall", "outage", "mttr"},
    "azure_devops": {"azure", "devops", "pipeline", "work", "item", "ado"},
}


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[a-z0-9]+", text.lower())}


def route_connectors_semantic(prompt: str, *, confidence_threshold: float = 0.15) -> tuple[list[str], float]:
    """Score connectors by token overlap; fall back to keyword router on low confidence."""
    tokens = _tokenize(prompt)
    if not tokens:
        return keyword_route(prompt), 0.0

    scores: dict[str, float] = {}
    for name, vocab in _CONNECTOR_VECTORS.items():
        overlap = len(tokens & vocab)
        scores[name] = overlap / max(1, len(vocab))

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top_score = ranked[0][1] if ranked else 0.0
    if top_score < confidence_threshold:
        return keyword_route(prompt), top_score

    selected = [name for name, score in ranked if score >= confidence_threshold * 0.5][:4]
    if not selected:
        return keyword_route(prompt), top_score
    return selected, top_score
