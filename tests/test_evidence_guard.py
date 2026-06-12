from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aaf.config import Settings
from aaf.schema import EvidenceRecord
from guardrails.evidence_guard import check_evidence, enforce_evidence
from guardrails.exceptions import GuardrailBlockedError


def _record(source: str = "github", summary: str = "CI failed") -> EvidenceRecord:
    return EvidenceRecord(source=source, kind="workflow_run", summary=summary, severity=0.7)


def test_redacts_pii_in_evidence_summary():
    evidence = [_record(summary="Notify bob@example.com about failure")]
    result = check_evidence(evidence, {}, Settings())
    assert result.passed
    assert "[REDACTED_EMAIL]" in result.sanitized_evidence[0].summary


def test_blocks_stale_ratio_above_threshold():
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    evidence = [
        EvidenceRecord(
            source="github",
            kind="workflow_run",
            summary="old run",
            severity=0.6,
            metadata={"observed_at": stale_time},
        ),
        EvidenceRecord(
            source="jira",
            kind="blocked_issue",
            summary="old issue",
            severity=0.8,
            metadata={"observed_at": stale_time},
        ),
    ]
    raw = {
        "github": {"simulated": True, "_fetched_at": stale_time},
        "jira": {"simulated": True, "_fetched_at": stale_time},
    }
    result = check_evidence(evidence, raw, Settings(evidence_stale_ratio_block=0.5))
    assert result.blocked
    assert any(v.rule == "stale_ratio" for v in result.violations)


def test_blocks_oversized_total_package():
    evidence = [_record(summary=f"row-{i}") for i in range(25)]
    result = check_evidence(evidence, {}, Settings(evidence_max_total=20))
    assert result.blocked
    assert any(v.rule == "max_total" for v in result.violations)


def test_blocks_per_source_over_cap():
    evidence = [_record(source="github", summary=f"row-{i}") for i in range(12)]
    result = check_evidence(evidence, {}, Settings(max_evidence_per_source=10))
    assert result.blocked
    assert any(v.rule == "max_per_source" for v in result.violations)


def test_enforce_raises_on_block():
    evidence = [_record(source="github", summary=f"row-{i}") for i in range(12)]
    with pytest.raises(GuardrailBlockedError):
        enforce_evidence(evidence, {}, Settings(max_evidence_per_source=10))
