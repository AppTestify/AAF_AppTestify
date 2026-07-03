"""Shared guardrail result types."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from aaf.schema import AgentOpinion, EvidenceRecord

GuardrailSeverity = Literal["warn", "block"]


class GuardrailViolation(BaseModel):
    rule: str
    severity: GuardrailSeverity
    message: str


class GuardrailResult(BaseModel):
    guard_name: str
    passed: bool
    blocked: bool = False
    violations: list[GuardrailViolation] = Field(default_factory=list)
    sanitized_prompt: str = ""
    sanitized_evidence: list[EvidenceRecord] = Field(default_factory=list)
    sanitized_agent_opinion: Optional[AgentOpinion] = None
    sanitized_explanation: str = ""
    metadata: dict[str, str] = Field(default_factory=dict)
