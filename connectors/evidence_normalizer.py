"""Map connector-specific payloads to canonical EvidenceRecord list."""

from __future__ import annotations

from typing import Any

from aaf.config import get_settings
from aaf.schema import EvidenceRecord


def _cap_per_source(recs: list[EvidenceRecord], limit: int) -> list[EvidenceRecord]:
    if len(recs) <= limit:
        return recs
    sorted_recs = sorted(recs, key=lambda r: r.severity, reverse=True)
    return sorted_recs[:limit]


def normalize_all(raw_by_connector: dict[str, dict[str, Any]]) -> list[EvidenceRecord]:
    limit = get_settings().max_evidence_per_source
    out: list[EvidenceRecord] = []
    truncated = 0
    for source, payload in raw_by_connector.items():
        if source == "github":
            batch = _github(payload)
        elif source == "jira":
            batch = _jira(payload)
        elif source == "finops":
            batch = _finops(payload)
        else:
            batch = []
        if len(batch) > limit:
            truncated += len(batch) - limit
        out.extend(_cap_per_source(batch, limit))
    if truncated:
        out.append(
            EvidenceRecord(
                source="system",
                kind="evidence_truncated",
                summary=f"Truncated {truncated} lower-severity evidence rows (max {limit} per source)",
                severity=0.1,
                metadata={"truncated_count": truncated, "max_per_source": limit},
            )
        )
    return out


def _github(p: dict[str, Any]) -> list[EvidenceRecord]:
    recs: list[EvidenceRecord] = []
    for pr in p.get("pull_requests") or []:
        state = (pr.get("state") or "").lower()
        title = pr.get("title") or "PR"
        draft = pr.get("draft", False)
        sev = 0.35 if draft else 0.25
        if state == "open":
            recs.append(
                EvidenceRecord(
                    source="github",
                    kind="open_pr",
                    summary=title[:200],
                    severity=min(1.0, sev + 0.1 * (1 if "block" in title.lower() else 0)),
                    metadata={"number": pr.get("number")},
                )
            )
    for run in p.get("workflow_runs") or []:
        status = (run.get("status") or "").lower()
        conclusion = (run.get("conclusion") or "").lower()
        name = run.get("name") or "workflow"
        sev = 0.2
        if conclusion == "failure":
            sev = 0.85
        elif conclusion == "cancelled":
            sev = 0.5
        elif status == "completed" and conclusion == "success":
            sev = 0.15
        recs.append(
            EvidenceRecord(
                source="github",
                kind="workflow_run",
                summary=f"{name}: {conclusion or status}",
                severity=sev,
                metadata={"id": run.get("id")},
            )
        )
    for issue in p.get("issues") or []:
        if "pull_request" in issue:
            continue
        title = issue.get("title") or "issue"
        labels = [x.get("name", "") for x in (issue.get("labels") or [])]
        sev = 0.4
        if any("bug" in x.lower() for x in labels):
            sev = 0.65
        recs.append(
            EvidenceRecord(
                source="github",
                kind="open_issue",
                summary=title[:200],
                severity=sev,
                metadata={"labels": labels},
            )
        )
    return recs


def _jira(p: dict[str, Any]) -> list[EvidenceRecord]:
    recs: list[EvidenceRecord] = []
    base_url = p.get("_base_url", "https://jira.atlassian.net")
    for item in p.get("issues") or []:
        fields = item.get("fields") or {}
        summary = fields.get("summary") or "issue"
        status = (fields.get("status") or {}).get("name") or ""
        st = status.lower()
        sev = 0.35
        kind = "jira_issue"
        if "block" in st or "blocked" in summary.lower():
            kind = "blocked_issue"
            sev = 0.8
        if any(x in st for x in ("done", "closed", "resolved")):
            continue
            
        key = item.get("key", "")
        url = f"{base_url}/browse/{key}" if key else ""
        
        recs.append(
            EvidenceRecord(
                source="jira",
                kind=kind,
                summary=f"{summary} [{status}]",
                severity=sev,
                metadata={"key": key, "url": url},
            )
        )
    return recs


def _finops(p: dict[str, Any]) -> list[EvidenceRecord]:
    recs: list[EvidenceRecord] = []
    for row in p.get("daily_spend") or []:
        amt = float(row.get("amount_usd") or 0)
        day = row.get("day") or ""
        baseline = float(row.get("baseline_usd") or max(1.0, amt))
        delta = abs(amt - baseline) / baseline
        sev = min(1.0, 0.3 + delta)
        recs.append(
            EvidenceRecord(
                source="finops",
                kind="daily_spend",
                summary=f"Spend {amt:.2f} vs baseline {baseline:.2f} on {day}",
                severity=sev,
                metadata=row,
            )
        )
    for a in p.get("anomalies") or []:
        recs.append(
            EvidenceRecord(
                source="finops",
                kind="cost_anomaly",
                summary=a.get("description") or "Cost anomaly",
                severity=float(a.get("severity", 0.7)),
                metadata=a,
            )
        )
    if p.get("rows"):
        for r in p["rows"][:50]:
            recs.append(
                EvidenceRecord(
                    source="finops",
                    kind="csv_row",
                    summary=str(r)[:200],
                    severity=0.35,
                    metadata=dict(r),
                )
            )
    return recs


def enrich_for_rar(evidence: list[EvidenceRecord], loop: int) -> list[EvidenceRecord]:
    """Re-ground: duplicate high-severity signals with slight boost and add trace."""
    boosted: list[EvidenceRecord] = []
    for e in evidence:
        if e.severity >= 0.55:
            boosted.append(
                EvidenceRecord(
                    source=e.source,
                    kind=e.kind + "_rar_confirm",
                    summary=f"[RAR{loop}] " + e.summary,
                    severity=min(1.0, e.severity + 0.08),
                    metadata={**e.metadata, "rar_loop": loop},
                )
            )
    extra = EvidenceRecord(
        source="system",
        kind="rar_reground",
        summary=f"Additional cross-check pass {loop} consolidated operational context.",
        severity=0.45 + 0.05 * loop,
        metadata={"rar_loop": loop},
    )
    return [*evidence, *boosted, extra]
