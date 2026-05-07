"""Fetch connector evidence, normalize, and run the pipeline."""

from __future__ import annotations

from typing import Any

from aaf.config import Settings
from aaf.schema import EvidenceRecord, PipelineResult
from app.services.llm_runtime import ActiveProvider
from connectors.evidence_normalizer import normalize_all
from connectors.finops_connector import FinopsConnector
from connectors.github_connector import GitHubConnector
from connectors.jira_connector import JiraConnector
from orchestrator.pipeline import run_pipeline
from pm_interface.router import route_connectors


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
    return raw


async def run_governance(
    prompt: str,
    prompt_id: str | None,
    settings: Settings,
    llm_providers: list[ActiveProvider] | None = None,
) -> PipelineResult:
    names = route_connectors(prompt)
    ctx: dict[str, str] = {"prompt": prompt, "github_repo": settings.github_repo, "jira_project": "PROJ"}
    raw = await _fetch_raw_evidence(settings, names, ctx)
    normalized = normalize_all(raw)

    async def live_refresh_evidence() -> list[EvidenceRecord]:
        raw_fresh = await _fetch_raw_evidence(settings, names, ctx)
        return normalize_all(raw_fresh)

    return await run_pipeline(
        prompt=prompt,
        prompt_id=prompt_id,
        settings=settings,
        normalized_evidence=normalized,
        raw_evidence_by_connector=raw,
        connectors_used=names,
        llm_providers=llm_providers or [],
        live_refresh_evidence=live_refresh_evidence,
    )
