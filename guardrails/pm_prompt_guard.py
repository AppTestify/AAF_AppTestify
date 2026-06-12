"""PM prompt input guardrail — injection, PII, length."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from guardrails.pii import redact_pii_text
from guardrails.types import GuardrailResult, GuardrailViolation

if TYPE_CHECKING:
    from aaf.config import Settings

_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_instructions",
        re.compile(
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
            re.IGNORECASE,
        ),
    ),
    (
        "disregard_system",
        re.compile(
            r"disregard\s+(your|the)\s+(system|developer)\s+(prompt|instructions?)",
            re.IGNORECASE,
        ),
    ),
    (
        "role_override",
        re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    ),
    (
        "act_as_override",
        re.compile(r"act\s+as\s+(a|an)\s+(different|new|unrestricted)\s+", re.IGNORECASE),
    ),
    (
        "chat_template_injection",
        re.compile(r"<\|im_start\|>|\[INST\]|<<SYS>>", re.IGNORECASE),
    ),
    (
        "system_prefix_injection",
        re.compile(r"(?m)^\s*system\s*:\s*", re.IGNORECASE),
    ),
    (
        "jinja_injection",
        re.compile(r"\{\{.*\}\}|\{%.*%\}"),
    ),
]

def check_pm_prompt(prompt: str, settings: Settings | None = None) -> GuardrailResult:
    """Validate and sanitize a PM governance prompt."""
    from aaf.config import Settings as SettingsCls

    cfg = settings or SettingsCls()
    max_len = cfg.pm_prompt_max_length
    text = prompt.strip()
    violations: list[GuardrailViolation] = []
    blocked = False

    if not text:
        violations.append(
            GuardrailViolation(rule="empty_prompt", severity="block", message="Prompt cannot be empty")
        )
        blocked = True

    if len(text) > max_len:
        violations.append(
            GuardrailViolation(
                rule="max_length",
                severity="block",
                message=f"Prompt exceeds maximum length of {max_len} characters",
            )
        )
        blocked = True

    for rule_id, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            violations.append(
                GuardrailViolation(
                    rule=rule_id,
                    severity="block",
                    message=f"Prompt injection pattern detected: {rule_id}",
                )
            )
            blocked = True

    sanitized, pii_rules = redact_pii_text(text)
    for rule_id in pii_rules:
        violations.append(
            GuardrailViolation(
                rule=rule_id,
                severity="warn",
                message=f"PII redacted from prompt ({rule_id})",
            )
        )

    passed = not blocked
    return GuardrailResult(
        guard_name="pm_prompt_guard",
        passed=passed,
        blocked=blocked,
        violations=violations,
        sanitized_prompt=sanitized,
        metadata={"original_length": str(len(prompt)), "sanitized_length": str(len(sanitized))},
    )


def enforce_pm_prompt(prompt: str, settings: Settings | None = None) -> str:
    """Run PM prompt guard; raise GuardrailBlockedError on hard block."""
    from guardrails.exceptions import GuardrailBlockedError

    result = check_pm_prompt(prompt, settings)
    if result.blocked:
        raise GuardrailBlockedError(result)
    return result.sanitized_prompt
