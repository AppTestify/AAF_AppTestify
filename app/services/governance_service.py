"""Fetch connector evidence, normalize, and run the pipeline."""

from __future__ import annotations

from typing import Any

from aaf.config import Settings
from aaf.schema import EvidenceRecord, PipelineResult
from app.services.llm_runtime import ActiveProvider
from connectors.evidence_normalizer import normalize_all
from connectors.azure_connector import AzureDevOpsConnector
from connectors.bitbucket_connector import BitbucketConnector
from connectors.finops_connector import FinopsConnector
from connectors.github_connector import GitHubConnector
from connectors.gitlab_connector import GitLabConnector
from connectors.jira_connector import JiraConnector
from connectors.pagerduty_connector import PagerDutyConnector
from datetime import datetime, timezone

from guardrails.pipeline import run_input_guards
from orchestrator.connector_router import route_connectors_semantic
from orchestrator.pipeline import run_pipeline
from tools.context import build_tool_context


async def _fetch_raw_evidence(settings: Settings, names: list[str], ctx: dict[str, str]) -> dict[str, dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = {}
    if "github" in names:
        gh = GitHubConnector(settings)
        raw["github"] = await gh.fetch_evidence(ctx)  # type: ignore[arg-type]
    if "jira" in names:
        ji = JiraConnector(settings)
        raw["jira"] = await ji.fetch_evidence(ctx)  # type: ignore[arg-type]
    if "finops" in names:
        fo = FinopsConnector(settings)
        raw["finops"] = await fo.fetch_evidence(ctx)  # type: ignore[arg-type]
    if "gitlab" in names:
        gl = GitLabConnector(settings)
        raw["gitlab"] = await gl.fetch_evidence(ctx)  # type: ignore[arg-type]
    if "bitbucket" in names:
        bb = BitbucketConnector(settings)
        raw["bitbucket"] = await bb.fetch_evidence(ctx)  # type: ignore[arg-type]
    if "pagerduty" in names:
        pd = PagerDutyConnector(settings)
        raw["pagerduty"] = await pd.fetch_evidence(ctx)  # type: ignore[arg-type]
    if "azure_devops" in names:
        az = AzureDevOpsConnector(settings)
        raw["azure_devops"] = await az.fetch_evidence(ctx)  # type: ignore[arg-type]
    return raw


async def run_governance(
    prompt: str,
    prompt_id: str | None,
    settings: Settings,
    llm_providers: list[ActiveProvider] | None = None,
) -> PipelineResult:
    names, _routing_confidence = route_connectors_semantic(prompt)
    ctx: dict[str, str] = {
        "prompt": prompt,
        "github_repo": settings.github_repo,
        "jira_project": settings.jira_project,
    }
    tool_ctx = build_tool_context(
        settings,
        github_repo=settings.github_repo,
        jira_project=settings.jira_project,
        jira_board_id=settings.jira_board_id,
    )
    raw = await _fetch_raw_evidence(settings, names, ctx)
    fetched_at = datetime.now(timezone.utc).isoformat()
    for payload in raw.values():
        if isinstance(payload, dict):
            payload["_fetched_at"] = fetched_at
    normalized = normalize_all(raw)
    guard_outcome = run_input_guards(prompt, normalized, raw, settings)
    prompt = guard_outcome.prompt
    normalized = guard_outcome.evidence

    async def live_refresh_evidence() -> list[EvidenceRecord]:
        raw_fresh = await _fetch_raw_evidence(settings, names, ctx)
        for payload in raw_fresh.values():
            if isinstance(payload, dict):
                payload["_fetched_at"] = datetime.now(timezone.utc).isoformat()
        fresh_normalized = normalize_all(raw_fresh)
        fresh_outcome = run_input_guards(prompt, fresh_normalized, raw_fresh, settings)
        return fresh_outcome.evidence

    return await run_pipeline(
        prompt=prompt,
        prompt_id=prompt_id,
        settings=settings,
        normalized_evidence=normalized,
        raw_evidence_by_connector=raw,
        connectors_used=names,
        llm_providers=llm_providers or [],
        live_refresh_evidence=live_refresh_evidence,
        tool_ctx=tool_ctx,
        input_guard_reports=guard_outcome.reports,
    )
