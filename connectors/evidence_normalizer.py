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
        elif source == "gitlab":
            batch = _gitlab(payload)
        elif source == "pagerduty":
            batch = _pagerduty(payload)
        elif source == "bitbucket":
            batch = _bitbucket(payload)
        elif source == "azure_devops":
            batch = _azure_devops(payload)
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


def _github_repo_base(p: dict[str, Any]) -> str:
    owner = p.get("owner")
    name = p.get("repo")
    if owner and name:
        return f"https://github.com/{owner}/{name}"
    return ""


def _github_pr_url(p: dict[str, Any], pr: dict[str, Any]) -> str:
    if pr.get("html_url"):
        return str(pr["html_url"])
    base = _github_repo_base(p)
    number = pr.get("number")
    if base and number is not None:
        return f"{base}/pull/{number}"
    return ""


def _github(p: dict[str, Any]) -> list[EvidenceRecord]:
    recs: list[EvidenceRecord] = []
    repo_base = _github_repo_base(p)
    for pr in p.get("pull_requests") or []:
        state = (pr.get("state") or "").lower()
        title = pr.get("title") or "PR"
        draft = pr.get("draft", False)
        sev = 0.35 if draft else 0.25
        if state == "open":
            number = pr.get("number")
            url = _github_pr_url(p, pr)
            recs.append(
                EvidenceRecord(
                    source="github",
                    kind="open_pr",
                    summary=title[:200],
                    severity=min(1.0, sev + 0.1 * (1 if "block" in title.lower() else 0)),
                    metadata={"number": number, "url": url, "repo": repo_base or None},
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
        run_url = run.get("html_url") or ""
        if not run_url and repo_base and run.get("id") is not None:
            run_url = f"{repo_base}/actions/runs/{run['id']}"
        recs.append(
            EvidenceRecord(
                source="github",
                kind="workflow_run",
                summary=f"{name}: {conclusion or status}",
                severity=sev,
                metadata={"id": run.get("id"), "url": run_url or None, "repo": repo_base or None},
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
        issue_url = issue.get("html_url") or ""
        if not issue_url and repo_base and issue.get("number") is not None:
            issue_url = f"{repo_base}/issues/{issue['number']}"
        recs.append(
            EvidenceRecord(
                source="github",
                kind="open_issue",
                summary=title[:200],
                severity=sev,
                metadata={
                    "labels": labels,
                    "number": issue.get("number"),
                    "url": issue_url or None,
                    "repo": repo_base or None,
                },
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
        
        summary_text = f"{key}: {summary} [{status}]" if key else f"{summary} [{status}]"
        recs.append(
            EvidenceRecord(
                source="jira",
                kind=kind,
                summary=summary_text,
                severity=sev,
                metadata={"key": key, "url": url, "jira_base_url": base_url},
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


def _gitlab(p: dict[str, Any]) -> list[EvidenceRecord]:
    recs: list[EvidenceRecord] = []
    project = p.get("project_id") or ""
    
    for mr in p.get("merge_requests") or []:
        state = (mr.get("state") or "").lower()
        title = mr.get("title") or "MR"
        is_wip = mr.get("work_in_progress", False) or mr.get("draft", False)
        
        sev = 0.35 if is_wip else 0.25
        if "block" in title.lower():
            sev += 0.1
        sev = round(min(1.0, sev), 2)
            
        if state in {"opened", "open"}:
            url = mr.get("web_url") or ""
            recs.append(
                EvidenceRecord(
                    source="gitlab",
                    kind="open_mr",
                    summary=title[:200],
                    severity=sev,
                    metadata={
                        "id": mr.get("id"),
                        "iid": mr.get("iid"),
                        "url": url or None,
                        "project": project or None,
                    },
                )
            )

    for pipe in p.get("pipelines") or []:
        status = (pipe.get("status") or "").lower()
        pipeline_id = pipe.get("id")
        
        sev = 0.2
        if status in {"failed", "failed"}:
            sev = 0.85
        elif status in {"canceled", "cancelled"}:
            sev = 0.5
        elif status == "success":
            sev = 0.15
            
        url = pipe.get("web_url") or ""
        recs.append(
            EvidenceRecord(
                source="gitlab",
                kind="pipeline",
                summary=f"Pipeline #{pipeline_id}: {status}",
                severity=sev,
                metadata={
                    "id": pipeline_id,
                    "url": url or None,
                    "project": project or None,
                },
            )
        )

    for issue in p.get("issues") or []:
        state = (issue.get("state") or "").lower()
        if state not in {"opened", "open"}:
            continue
            
        title = issue.get("title") or "issue"
        labels = issue.get("labels") or []
        label_names = [
            x.get("name", "") if isinstance(x, dict) else str(x)
            for x in labels
        ]
        
        sev = 0.4
        if any("bug" in x.lower() for x in label_names):
            sev = 0.65
            
        url = issue.get("web_url") or ""
        recs.append(
            EvidenceRecord(
                source="gitlab",
                kind="open_issue",
                summary=title[:200],
                severity=sev,
                metadata={
                    "id": issue.get("id"),
                    "iid": issue.get("iid"),
                    "labels": label_names,
                    "url": url or None,
                    "project": project or None,
                },
            )
        )
        
    return recs


def _pagerduty(p: dict[str, Any]) -> list[EvidenceRecord]:
    """Normalize PagerDuty incidents to EvidenceRecords.
    
    Severity calculation:
    - Base: 0.3 (low urgency, resolved) to 0.75 (high urgency)
    - Adjustment: +0.15 if unresolved/triggered
    - Final: clamped to [0.0, 1.0]
    """
    recs: list[EvidenceRecord] = []
    
    for incident in p.get("incidents") or []:
        incident_id = incident.get("id") or ""
        title = incident.get("title") or incident.get("summary") or "Incident"
        status = (incident.get("status") or "").lower()
        urgency = (incident.get("urgency") or "").lower()
        web_url = incident.get("html_url") or incident.get("web_url") or ""
        mttr_hours = incident.get("mttr_hours")
        created_at = incident.get("created_at")
        resolved_at = incident.get("resolved_at")
        
        # Base severity by urgency
        if urgency == "high":
            sev = 0.75
        elif urgency == "medium":
            sev = 0.50
        else:
            sev = 0.30
        
        # Adjust for status: +0.15 if unresolved
        if status in {"triggered", "acknowledged"}:
            sev += 0.15
        
        # Clamp to [0.0, 1.0]
        sev = round(min(1.0, max(0.0, sev)), 2)
        
        recs.append(
            EvidenceRecord(
                source="pagerduty",
                kind="incident",
                summary=title[:200],
                severity=sev,
                metadata={
                    "id": incident_id,
                    "status": status,
                    "urgency": urgency,
                    "url": web_url or None,
                    "mttr_hours": mttr_hours,
                    "created_at": created_at,
                    "resolved_at": resolved_at,
                },
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

def _bitbucket(p: dict[str, Any]) -> list[EvidenceRecord]:
    recs: list[EvidenceRecord] = []
    workspace = p.get("workspace")
    repo = p.get("repo")
    repo_base = f"https://bitbucket.org/{workspace}/{repo}" if workspace and repo else ""

    for pr in p.get("pull_requests") or []:
        state = (pr.get("state") or "").lower()
        title = pr.get("title") or "PR"
        url = ((pr.get("links") or {}).get("html") or {}).get("href") or repo_base
        if state == "open":
            sev = 0.25 + 0.1 * (1 if "block" in title.lower() else 0)
            recs.append(
                EvidenceRecord(
                    source="bitbucket",
                    kind="open_pr",
                    summary=title[:200],
                    severity=min(1.0, sev),
                    metadata={"url": url, "repo": repo_base or None},
                )
            )

    for pipe in p.get("pipelines") or []:
        state_dict = pipe.get("state") or {}
        state_name = (state_dict.get("name") or "").lower()
        result_dict = state_dict.get("result") or {}
        result_name = (result_dict.get("name") or "").lower()
        
        url = ((pipe.get("repository") or {}).get("links") or {}).get("html") or {}
        url = url.get("href") or repo_base
        
        if state_name == "completed" and result_name == "failed":
            recs.append(
                EvidenceRecord(
                    source="bitbucket",
                    kind="failed_pipeline",
                    summary="Bitbucket pipeline failed",
                    severity=0.85,
                    metadata={"url": url},
                )
            )

    for issue in p.get("issues") or []:
        state = (issue.get("state") or "").lower()
        title = issue.get("title") or "Issue"
        priority = (issue.get("priority") or "").lower()
        url = ((issue.get("links") or {}).get("html") or {}).get("href") or repo_base
        
        if state in {"new", "open"}:
            sev = 0.5 if priority in {"major", "critical", "blocker"} else 0.3
            recs.append(
                EvidenceRecord(
                    source="bitbucket",
                    kind="open_issue",
                    summary=title[:200],
                    severity=sev,
                    metadata={"url": url},
                )
            )

    return recs

def _azure_devops(p: dict[str, Any]) -> list[EvidenceRecord]:
    recs: list[EvidenceRecord] = []
    
    # Process pull requests
    for pr in p.get("pull_requests") or []:
        status = (pr.get("status") or "").lower()
        title = pr.get("title") or "PR"
        url = pr.get("url") or ""
        is_draft = pr.get("isDraft", False)
        sev = 0.35 if is_draft else 0.25
        if status == "active":
            recs.append(
                EvidenceRecord(
                    source="azure_devops",
                    kind="open_pr",
                    summary=title[:200],
                    severity=min(1.0, sev + 0.1 * (1 if "block" in title.lower() else 0)),
                    metadata={"url": url, "pr_id": pr.get("pullRequestId")},
                )
            )

    # Process pipelines (builds)
    for build in p.get("pipelines") or []:
        result = (build.get("result") or "").lower()
        status = (build.get("status") or "").lower()
        name = (build.get("definition") or {}).get("name") or "Build"
        url = (build.get("_links") or {}).get("web") or {}
        url = url.get("href") or ""
        
        if result == "failed":
            recs.append(
                EvidenceRecord(
                    source="azure_devops",
                    kind="failed_pipeline",
                    summary=f"{name} pipeline failed",
                    severity=0.85,
                    metadata={"url": url, "build_id": build.get("id")},
                )
            )
            
    # Process work items
    for item in p.get("work_items") or []:
        fields = item.get("fields") or {}
        state = (fields.get("System.State") or "").lower()
        title = fields.get("System.Title") or "Work Item"
        item_type = (fields.get("System.WorkItemType") or "").lower()
        url = (item.get("_links") or {}).get("html") or {}
        url = url.get("href") or ""
        
        if state not in {"closed", "done", "removed"}:
            sev = 0.5 if item_type in {"bug", "issue"} else 0.3
            recs.append(
                EvidenceRecord(
                    source="azure_devops",
                    kind="work_item",
                    summary=title[:200],
                    severity=sev,
                    metadata={"url": url, "item_id": item.get("id")},
                )
            )

    return recs
