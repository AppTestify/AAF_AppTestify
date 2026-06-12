"""Canonical AgileOps agent tool registry — single source of truth."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "data" / "tool_registry.json"

ToolMethod = Literal["direct_api", "api_mcp", "mcp", "roadmap"]
ToolStatus = Literal["shipped", "pending", "roadmap"]


class PMScenario(BaseModel):
    title: str
    narrative: str


class ToolRegistryEntry(BaseModel):
    id: str
    function_name: str
    agent_id: str
    display_agent: str
    method: ToolMethod
    implementation_status: ToolStatus
    weight: float = 0.0
    jira_task: Optional[str] = None
    extension: bool = False
    system: str = ""
    auth: str = ""
    api_endpoints: list[str] = Field(default_factory=list)
    mcp_mappings: list[str] = Field(default_factory=list)
    fires_when: str = ""
    returns: list[str] = Field(default_factory=list)
    pm_scenario: PMScenario


class AgentRegistryMeta(BaseModel):
    label: str
    summary: str


class AgentRegistrySection(BaseModel):
    id: str
    label: str
    summary: str
    tools: list[ToolRegistryEntry]


class ToolRegistryDocument(BaseModel):
    version: int
    agents: dict[str, AgentRegistryMeta]
    tools: list[ToolRegistryEntry]


class ToolRegistryResponse(BaseModel):
    agents: list[AgentRegistrySection]
    meta: dict[str, int]


@lru_cache(maxsize=1)
def load_tool_registry() -> ToolRegistryDocument:
    raw = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    return ToolRegistryDocument.model_validate(raw)


def registry_allowlist(*, shipped_only: bool = True) -> dict[str, frozenset[str]]:
    """Derive guardrail allowlist from registry."""
    doc = load_tool_registry()
    out: dict[str, set[str]] = {}
    for entry in doc.tools:
        if shipped_only and entry.implementation_status != "shipped":
            continue
        out.setdefault(entry.agent_id, set()).add(entry.function_name)
    return {k: frozenset(v) for k, v in out.items()}


def shipped_tools(agent_id: str) -> list[ToolRegistryEntry]:
    return [t for t in load_tool_registry().tools if t.agent_id == agent_id and t.implementation_status == "shipped"]


def filter_registry(
    *,
    agent: Optional[str] = None,
    status: Optional[str] = None,
    method: Optional[str] = None,
) -> ToolRegistryResponse:
    doc = load_tool_registry()
    tools = list(doc.tools)
    if agent:
        tools = [t for t in tools if t.agent_id == agent]
    if status and status != "all":
        tools = [t for t in tools if t.implementation_status == status]
    if method:
        tools = [t for t in tools if t.method == method]

    by_agent: dict[str, list[ToolRegistryEntry]] = {}
    for t in tools:
        by_agent.setdefault(t.agent_id, []).append(t)

    sections: list[AgentRegistrySection] = []
    for agent_id, meta in doc.agents.items():
        if agent_id not in by_agent:
            continue
        sections.append(
            AgentRegistrySection(
                id=agent_id,
                label=meta.label,
                summary=meta.summary,
                tools=sorted(by_agent[agent_id], key=lambda x: x.function_name),
            )
        )

    all_tools = doc.tools
    return ToolRegistryResponse(
        agents=sections,
        meta={
            "total_count": len(all_tools),
            "shipped_count": sum(1 for t in all_tools if t.implementation_status == "shipped"),
            "pending_count": sum(1 for t in all_tools if t.implementation_status == "pending"),
            "roadmap_count": sum(1 for t in all_tools if t.implementation_status == "roadmap"),
            "filtered_count": len(tools),
        },
    )


def entry_returns_map() -> dict[str, list[str]]:
    return {t.function_name: t.returns for t in load_tool_registry().tools if t.implementation_status == "shipped"}
