"""Route PM prompts to relevant connectors (keyword heuristics)."""

from __future__ import annotations

import re

_GITHUB = re.compile(
    r"\b(github|pull request|pr|workflow|ci|cd|build|commit|release|merge|repo)\b",
    re.I,
)
_JIRA = re.compile(
    r"\b(jira|sprint|ticket|story|epic|blocked|backlog|defect|escalat|delivery)\b",
    re.I,
)
_FINOPS = re.compile(
    r"\b(cost|finops|budget|spend|cloud bill|anomal|aws|azure|gcp|capacity|scale|autoscaling)\b",
    re.I,
)


def route_connectors(prompt: str) -> list[str]:
    p = prompt.strip()
    if not p:
        return ["github", "jira", "finops"]
    out: list[str] = []
    if _GITHUB.search(p):
        out.append("github")
    if _JIRA.search(p):
        out.append("jira")
    if _FINOPS.search(p):
        out.append("finops")
    if not out:
        return ["github", "jira", "finops"]
    return list(dict.fromkeys(out))
