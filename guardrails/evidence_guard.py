"""Evidence input guardrail — PII, size, stale data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from aaf.schema import EvidenceRecord
from guardrails.exceptions import GuardrailBlockedError
from guardrails.pii import redact_pii_text
from guardrails.types import GuardrailResult, GuardrailViolation

if TYPE_CHECKING:
    from aaf.config import Settings


def _parse_iso_ts(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _connector_is_stale(source_raw: dict[str, Any], stale_hours: float) -> bool:
    if source_raw.get("error"):
        return True
    if source_raw.get("stale") is True:
        return True
    freshness = str(source_raw.get("freshness") or source_raw.get("_freshness") or "").lower()
    if freshness in {"stale", "degraded"}:
        return True
    fetched = _parse_iso_ts(source_raw.get("_fetched_at") or source_raw.get("captured_at"))
    if fetched is None:
        return False
    age_hours = (datetime.now(timezone.utc) - fetched).total_seconds() / 3600
    return age_hours > stale_hours


def _record_is_stale(
    record: EvidenceRecord,
    raw_by_connector: dict[str, dict[str, Any]],
    stale_hours: float,
) -> bool:
    if record.source == "system":
        return False
    if record.metadata.get("stale") is True:
        return True

    source_raw = raw_by_connector.get(record.source, {})
    if isinstance(source_raw, dict) and _connector_is_stale(source_raw, stale_hours):
        return True

    for key in ("observed_at", "updated_at", "fetched_at", "created_at", "captured_at"):
        ts = _parse_iso_ts(record.metadata.get(key))
        if ts is None:
            continue
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        return age_hours > stale_hours
    return False


def _redact_record(record: EvidenceRecord) -> tuple[EvidenceRecord, list[str]]:
    summary, matched = redact_pii_text(record.summary)
    redacted_metadata = dict(record.metadata)
    for key, value in record.metadata.items():
        if isinstance(value, str):
            redacted_value, meta_matches = redact_pii_text(value)
            if meta_matches:
                redacted_metadata[key] = redacted_value
                matched.extend(meta_matches)

    matched = list(dict.fromkeys(matched))
    if not matched:
        return record, []

    return record.model_copy(
        update={
            "summary": summary,
            "metadata": {**redacted_metadata, "pii_redacted": True},
        }
    ), matched


def check_evidence(
    evidence: list[EvidenceRecord],
    raw_by_connector: dict[str, dict[str, Any]] | None = None,
    settings: Settings | None = None,
) -> GuardrailResult:
    """Validate and sanitize normalized evidence before agents run."""
    from aaf.config import Settings as SettingsCls

    cfg = settings or SettingsCls()
    raw = raw_by_connector or {}
    violations: list[GuardrailViolation] = []
    blocked = False

    max_per_source = cfg.max_evidence_per_source
    max_total = cfg.evidence_max_total
    stale_ratio_limit = cfg.evidence_stale_ratio_block
    stale_hours = cfg.evidence_stale_hours

    per_source: dict[str, int] = {}
    for rec in evidence:
        per_source[rec.source] = per_source.get(rec.source, 0) + 1

    for source, count in per_source.items():
        if source == "system":
            continue
        if count > max_per_source:
            violations.append(
                GuardrailViolation(
                    rule="max_per_source",
                    severity="block",
                    message=f"Source {source} has {count} evidence rows (max {max_per_source})",
                )
            )
            blocked = True

    signal_records = [r for r in evidence if r.source != "system"]
    if len(evidence) > max_total:
        violations.append(
            GuardrailViolation(
                rule="max_total",
                severity="block",
                message=f"Evidence package has {len(evidence)} rows (max {max_total})",
            )
        )
        blocked = True

    stale_count = sum(1 for r in signal_records if _record_is_stale(r, raw, stale_hours))
    if signal_records:
        stale_ratio = stale_count / len(signal_records)
        if stale_ratio > stale_ratio_limit:
            violations.append(
                GuardrailViolation(
                    rule="stale_ratio",
                    severity="block",
                    message=(
                        f"Stale evidence ratio {stale_ratio:.0%} exceeds limit "
                        f"{stale_ratio_limit:.0%} ({stale_count}/{len(signal_records)} signals)"
                    ),
                )
            )
            blocked = True
        elif stale_count:
            violations.append(
                GuardrailViolation(
                    rule="stale_ratio",
                    severity="warn",
                    message=f"{stale_count} stale signal(s) detected",
                )
            )

    sanitized: list[EvidenceRecord] = []
    for rec in evidence:
        redacted, matched = _redact_record(rec)
        sanitized.append(redacted)
        for rule_id in matched:
            violations.append(
                GuardrailViolation(
                    rule=f"pii_{rule_id}",
                    severity="warn",
                    message=f"PII redacted from evidence ({rule_id})",
                )
            )

    return GuardrailResult(
        guard_name="evidence_guard",
        passed=not blocked,
        blocked=blocked,
        violations=violations,
        sanitized_evidence=sanitized,
        metadata={
            "signal_count": str(len(signal_records)),
            "stale_count": str(stale_count),
            "total_count": str(len(evidence)),
        },
    )


def enforce_evidence(
    evidence: list[EvidenceRecord],
    raw_by_connector: dict[str, dict[str, Any]] | None = None,
    settings: Settings | None = None,
) -> list[EvidenceRecord]:
    """Run evidence guard; raise GuardrailBlockedError on hard block."""
    result = check_evidence(evidence, raw_by_connector, settings)
    if result.blocked:
        raise GuardrailBlockedError(result)
    return list(result.sanitized_evidence)
