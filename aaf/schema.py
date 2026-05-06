"""Pydantic models for the governance pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RiskTheme(str, Enum):
    """Comparable risk themes for consensus."""

    OPERATIONAL_RISK = "operational_risk"
    COST_RISK = "cost_risk"
    SECURITY_RISK = "security_risk"
    DELIVERY_RISK = "delivery_risk"
    RELIABILITY_RISK = "reliability_risk"
    LOW_RISK = "low_risk"
    UNKNOWN = "unknown"


class GovernanceAction(str, Enum):
    """Candidate business actions for utility scoring."""

    ROLLBACK = "rollback"
    MITIGATE_MONITOR = "mitigate_monitor"
    SCALE_ADJUST = "scale_adjust"
    PATCH_BLOCK_RELEASE = "patch_block_release"
    OBSERVE = "observe"


class EvidenceRecord(BaseModel):
    """Canonical evidence after normalization."""

    source: str  # github | jira | finops
    kind: str  # e.g. pr_failed, blocked_issue, cost_spike
    summary: str
    severity: float = Field(ge=0.0, le=1.0, default=0.5)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentOpinion(BaseModel):
    """Single domain agent output."""

    agent_id: str
    claim: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: List[str] = Field(default_factory=list)
    risk_theme: RiskTheme = RiskTheme.UNKNOWN
    raw_signals: Dict[str, Any] = Field(default_factory=dict)


class ConsensusResult(BaseModel):
    consensus_score: float = Field(ge=0.0, le=1.0)
    theme_counts: Dict[str, int] = Field(default_factory=dict)
    dominant_theme: Optional[RiskTheme] = None
    notes: str = ""


class RARResult(BaseModel):
    rar_triggered: bool
    rar_loops: int
    consensus_before: float
    consensus_after: float
    reground_notes: List[str] = Field(default_factory=list)


class UtilityResult(BaseModel):
    recommended_action: GovernanceAction
    utility_score: float
    scores_by_action: Dict[str, float] = Field(default_factory=dict)
    weights_used: Dict[str, float] = Field(default_factory=dict)


class ExplainabilityResult(BaseModel):
    xi_score: float = Field(ge=0.0, le=1.0, description="Explainability index 0-1")
    checks: Dict[str, bool] = Field(default_factory=dict)


class PMFormattedDecision(BaseModel):
    title: str
    summary_markdown: str
    detail_json: Dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    """Full run output for API and UI."""

    prompt: str
    prompt_id: Optional[str] = None
    connectors_used: List[str] = Field(default_factory=list)
    raw_evidence_by_connector: Dict[str, Any] = Field(default_factory=dict)
    normalized_evidence: List[EvidenceRecord] = Field(default_factory=list)
    agent_opinions: List[AgentOpinion] = Field(default_factory=list)
    consensus: ConsensusResult
    rar: RARResult
    utility: UtilityResult
    explanation: str
    explainability: ExplainabilityResult
    pm_view: PMFormattedDecision
    llm_invocation: Dict[str, Any] = Field(default_factory=dict)
