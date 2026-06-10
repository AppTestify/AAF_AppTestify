"""Agent and tool schemas aligned with the spec."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from aaf.schema import EvidenceRecord


class ToolResult(BaseModel):
    """Output from a single agent tool."""

    tool_name: str
    signal: float = Field(ge=0.0, le=1.0, description="Risk signal 0=healthy, 1=critical")
    captured_at: datetime
    raw_signals: dict[str, Any] = Field(default_factory=dict)
    evidence_lines: list[str] = Field(default_factory=list)


class EvidencePackage(BaseModel):
    """Input bundle for BaseAgent."""

    records: list[EvidenceRecord] = Field(default_factory=list)
    prompt: str = ""


class AgentOutput(BaseModel):
    """Spec-aligned agent output."""

    claim: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
