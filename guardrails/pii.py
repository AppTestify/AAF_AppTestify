"""Shared PII detection and redaction."""

from __future__ import annotations

import re

PII_REDACTORS: list[tuple[str, re.Pattern[str], str]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED_SSN]"),
    (
        "phone",
        re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
]


def redact_pii_text(text: str) -> tuple[str, list[str]]:
    """Return redacted text and list of PII rule ids that matched."""
    redacted = text
    matched: list[str] = []
    for rule_id, pattern, replacement in PII_REDACTORS:
        if pattern.search(redacted):
            redacted = pattern.sub(replacement, redacted)
            matched.append(rule_id)
    return redacted, matched
