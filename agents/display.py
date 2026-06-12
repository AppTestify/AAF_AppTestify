"""Display identifiers for agents in API and UI."""

from __future__ import annotations

AGENT_DISPLAY_IDS: dict[str, str] = {
    "devops": "devops",
    "project_management": "pm",
    "finops": "finops",
    "devsecops": "secops",
}

AGENT_DISPLAY_LABELS: dict[str, str] = {
    "devops": "DevOps",
    "pm": "PM",
    "finops": "FinOps",
    "secops": "SecOps",
}


def resolve_display_id(agent_id: str) -> str:
    return AGENT_DISPLAY_IDS.get(agent_id, agent_id)


def resolve_display_label(agent_id: str, display_id: str | None = None) -> str:
    did = display_id or resolve_display_id(agent_id)
    return AGENT_DISPLAY_LABELS.get(did, did.replace("_", " ").title())
