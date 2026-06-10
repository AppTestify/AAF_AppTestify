"""Spec-aligned tool layer for domain agents."""

from tools.context import ToolContext, build_tool_context
from tools.scoring import ConfidenceScorer, apply_staleness_penalty

__all__ = [
    "ToolContext",
    "build_tool_context",
    "ConfidenceScorer",
    "apply_staleness_penalty",
]
