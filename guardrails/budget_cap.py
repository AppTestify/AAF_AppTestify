"""Workspace LLM budget cap and pre-run checks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.config import TenantSettings
from app.models.metrics import LLMCallLog
from guardrails.exceptions import GuardrailBlockedError
from guardrails.types import GuardrailResult, GuardrailViolation

if TYPE_CHECKING:
    from aaf.config import Settings


def _budget_from_settings_row(row: Optional[TenantSettings]) -> tuple[Optional[float], float]:
    """Return (monthly_budget_usd, alert_threshold_ratio) from tenant settings."""
    if row is None:
        return None, 0.8
    prefs = row.ui_preferences if isinstance(row.ui_preferences, dict) else {}
    budget = prefs.get("llm_monthly_budget_usd")
    alert_ratio = float(prefs.get("llm_budget_alert_ratio") or 0.8)
    if budget is None:
        return None, alert_ratio
    try:
        return float(budget), alert_ratio
    except (TypeError, ValueError):
        return None, alert_ratio


def monthly_spend_usd(db: Session, tenant_id: int) -> float:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = db.scalar(
        select(func.coalesce(func.sum(LLMCallLog.cost_usd), 0.0)).where(
            LLMCallLog.tenant_id == tenant_id,
            LLMCallLog.created_at >= month_start,
        )
    )
    return float(total or 0.0)


def check_budget_cap(
    db: Session,
    tenant_id: Optional[int],
    settings_row: Optional[TenantSettings],
    settings: Optional[Settings] = None,
) -> GuardrailResult:
    from aaf.config import Settings as SettingsCls

    cfg = settings or SettingsCls()
    if not cfg.guardrails_enabled or tenant_id is None:
        return GuardrailResult(guard_name="budget_cap", passed=True, violations=[])

    budget_usd, alert_ratio = _budget_from_settings_row(settings_row)
    if budget_usd is None or budget_usd <= 0:
        return GuardrailResult(guard_name="budget_cap", passed=True, violations=[])

    spent = monthly_spend_usd(db, tenant_id)
    utilization = spent / budget_usd if budget_usd else 0.0
    violations: list[GuardrailViolation] = []

    if utilization >= 1.0:
        violations.append(
            GuardrailViolation(
                rule="budget_exceeded",
                severity="block",
                message=f"Monthly LLM budget exceeded (${spent:.4f} / ${budget_usd:.2f})",
            )
        )
    elif utilization >= alert_ratio:
        violations.append(
            GuardrailViolation(
                rule="budget_warning",
                severity="warn",
                message=f"Monthly LLM budget at {utilization:.0%} (${spent:.4f} / ${budget_usd:.2f})",
            )
        )

    blocked = any(v.severity == "block" for v in violations)
    return GuardrailResult(
        guard_name="budget_cap",
        passed=not blocked,
        blocked=blocked,
        violations=violations,
        metadata={
            "spent_usd": f"{spent:.6f}",
            "budget_usd": f"{budget_usd:.2f}",
            "utilization": f"{utilization:.4f}",
        },
    )


def enforce_budget_cap(
    db: Session,
    tenant_id: Optional[int],
    settings_row: Optional[TenantSettings],
    settings: Optional[Settings] = None,
) -> GuardrailResult:
    result = check_budget_cap(db, tenant_id, settings_row, settings)
    if result.blocked:
        raise GuardrailBlockedError(result)
    return result


def budget_status_dict(db: Session, tenant_id: int, settings_row: Optional[TenantSettings]) -> dict[str, Any]:
    budget_usd, alert_ratio = _budget_from_settings_row(settings_row)
    spent = monthly_spend_usd(db, tenant_id)
    if budget_usd is None:
        return {"enabled": False, "spent_usd": spent}
    utilization = spent / budget_usd if budget_usd else 0.0
    return {
        "enabled": True,
        "budget_usd": budget_usd,
        "spent_usd": round(spent, 6),
        "utilization": round(utilization, 4),
        "alert_ratio": alert_ratio,
        "status": "exceeded" if utilization >= 1 else "warning" if utilization >= alert_ratio else "ok",
    }
