"""Guardrail exceptions."""

from __future__ import annotations

from guardrails.types import GuardrailResult


class GuardrailBlockedError(Exception):
    """Raised when a hard-block guardrail rejects pipeline input."""

    def __init__(self, result: GuardrailResult) -> None:
        self.result = result
        messages = [v.message for v in result.violations if v.severity == "block"]
        detail = "; ".join(messages) if messages else "Guardrail blocked this request"
        super().__init__(detail)
