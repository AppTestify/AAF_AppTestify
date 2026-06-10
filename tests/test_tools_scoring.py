"""Tests for tool layer and confidence scoring."""

from datetime import datetime, timedelta, timezone

import pytest

from agents.schemas import ToolResult
from tools.scoring import ConfidenceScorer, apply_staleness_penalty


def test_staleness_penalty_applied():
    now = datetime.now(timezone.utc)
    stale = now - timedelta(hours=5)
    fresh_signal = apply_staleness_penalty(0.8, now, staleness_hours=4.0, penalty_factor=0.5)
    stale_signal = apply_staleness_penalty(0.8, stale, staleness_hours=4.0, penalty_factor=0.5)
    assert fresh_signal == 0.8
    assert stale_signal == 0.4


def test_weighted_confidence_scorer():
    now = datetime.now(timezone.utc)
    results = [
        ToolResult(tool_name="get_ci_status", signal=0.8, captured_at=now, raw_signals={}),
        ToolResult(tool_name="get_deploy_history", signal=0.2, captured_at=now, raw_signals={}),
    ]
    weights = {"get_ci_status": 0.7, "get_deploy_history": 0.3}
    score = ConfidenceScorer.compute(results, weights, staleness_hours=4.0, penalty_factor=0.5)
    assert 0.5 < score < 0.7


@pytest.mark.asyncio
async def test_devops_tools_sim_mode(settings):
    from aaf.config import ConnectorMode
    from tools.context import build_tool_context
    from tools.devops import get_ci_status, detect_rollbacks, check_branch_protection

    settings.connector_mode = ConnectorMode.SIM
    ctx = build_tool_context(settings)

    ci = await get_ci_status(ctx)
    assert "ci_pass_rate" in ci.raw_signals
    assert ci.tool_name == "get_ci_status"

    rollback = await detect_rollbacks(ctx)
    assert "rollback_24h" in rollback.raw_signals

    protection = await check_branch_protection(ctx)
    assert "reviews_met" in protection.raw_signals


@pytest.mark.asyncio
async def test_pm_tools_sim_mode(settings):
    from aaf.config import ConnectorMode
    from tools.context import build_tool_context
    from tools.pm import count_blockers, get_sprint_status

    settings.connector_mode = ConnectorMode.SIM
    ctx = build_tool_context(settings)

    blockers = await count_blockers(ctx)
    assert blockers.raw_signals["blocked_count"] >= 1

    sprint = await get_sprint_status(ctx)
    assert "sprint_done_pct" in sprint.raw_signals


@pytest.mark.asyncio
async def test_finops_tools_sim_mode(settings):
    from aaf.config import ConnectorMode
    from tools.context import build_tool_context
    from tools.finops import get_spend_trend, check_budget_pace
    from tools.finops.reasoning import compute_ci_score, generate_cost_claim

    settings.connector_mode = ConnectorMode.SIM
    ctx = build_tool_context(settings)

    spend = await get_spend_trend(ctx)
    assert "wow_delta_pct" in spend.raw_signals
    assert spend.raw_signals.get("anomaly_flag") is True

    budget = await check_budget_pace(ctx)
    assert "pace_ratio" in budget.raw_signals

    results = [spend, budget]
    claim = generate_cost_claim(results)
    assert "cost" in claim.lower()
    ci = compute_ci_score(results)
    assert 0.0 <= ci <= 1.0


@pytest.mark.asyncio
async def test_devsecops_tools_sim_mode(settings):
    from aaf.config import ConnectorMode
    from tools.context import build_tool_context
    from tools.devsecops import scan_cves, scan_secrets

    settings.connector_mode = ConnectorMode.SIM
    ctx = build_tool_context(settings)

    cves = await scan_cves(ctx)
    assert "critical_count" in cves.raw_signals

    secrets = await scan_secrets(ctx)
    assert "secrets_detected" in secrets.raw_signals
