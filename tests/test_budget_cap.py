from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models.config import TenantSettings
from app.models.metrics import LLMCallLog
from app.models.tenant import Tenant
from guardrails.budget_cap import check_budget_cap, enforce_budget_cap
from guardrails.exceptions import GuardrailBlockedError


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    tenant = Tenant(slug="t1", name="T1", is_active=True)
    session.add(tenant)
    session.flush()
    session.add(
        TenantSettings(
            tenant_id=tenant.id,
            ui_preferences={"llm_monthly_budget_usd": 1.0, "llm_budget_alert_ratio": 0.8},
        )
    )
    session.add(
        LLMCallLog(
            tenant_id=tenant.id,
            agent_id="orchestrator",
            provider_name="openai",
            model_name="gpt-4o-mini",
            prompt_tokens=100,
            completion_tokens=50,
            cost_usd=1.5,
            latency_ms=10,
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()
    yield session, tenant
    session.close()


def test_blocks_when_budget_exceeded(db_session):
    db, tenant = db_session
    ts = db.query(TenantSettings).filter_by(tenant_id=tenant.id).one()
    result = check_budget_cap(db, tenant.id, ts)
    assert result.blocked
    with pytest.raises(GuardrailBlockedError):
        enforce_budget_cap(db, tenant.id, ts)


def test_passes_without_budget_configured(db_session):
    db, tenant = db_session
    ts = db.query(TenantSettings).filter_by(tenant_id=tenant.id).one()
    ts.ui_preferences = {}
    db.commit()
    result = check_budget_cap(db, tenant.id, ts)
    assert result.passed
