"""Background governance run worker (in-process queue for V1)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from queue import Queue
from threading import Lock, Thread
from typing import Optional

from sqlalchemy import select

from aaf.config import get_settings
from app import db as db_mod
from app.models.governance import AuditEvent, EvidenceSnapshot, GovernanceRun
from app.models.governance import AgentFinding, CorrelatedIncident, ExecutiveSummary
from app.models.config import TenantConnectorConfig, TenantSettings
from app.models.metrics import LLMCallLog
from app.models.tenant import Tenant
from app.models.user import User
from app.services.agentic_intelligence import (
    build_agent_findings_with_llm,
    build_executive_summary,
    build_incident,
    compute_consensus,
)
from app.services.config_resolver import apply_pipeline_overrides, get_ai_runtime_summary, resolve_effective_settings, resolve_tenant_for_user
from guardrails.budget_cap import enforce_budget_cap
from guardrails.exceptions import GuardrailBlockedError
from app.services.governance_service import run_governance
from app.services.llm_runtime import resolve_provider_chain
from app.services.integration_signals import connector_signal
from app.services.observability import record_connector_call, record_dead_letter, record_llm_invocation, record_run, set_run_queue_depth
from app.services.observability import snapshot as observability_snapshot
from app.services.decision_framing import orchestration_snapshot_from_run_payload
from app.services.run_payload import enrich_run_payload
from app.services.governance_delivery import deliver_run_complete_notifications
from pm_interface.decision_formatter import pipeline_result_to_jsonable

_queue: "Queue[int]" = Queue()
_thread: Optional[Thread] = None
_lock = Lock()
_stop = False
_MAX_RETRIES = 2
_log = logging.getLogger(__name__)


def start_worker() -> None:
    global _thread, _stop
    with _lock:
        _stop = False
        if _thread and _thread.is_alive():
            return
        _thread = Thread(target=_worker_loop, name="governance-run-worker", daemon=True)
        _thread.start()


def stop_worker() -> None:
    global _stop, _thread
    _stop = True
    _queue.put(-1)
    _thread = None


def _use_celery() -> bool:
    settings = get_settings()
    return bool(settings.celery_broker_url or settings.redis_url)


def enqueue_run(run_id: int) -> None:
    if _use_celery():
        from app.celery_app import process_run_task

        process_run_task.delay(run_id)
        set_run_queue_depth(1)
        return
    _queue.put(run_id)
    set_run_queue_depth(_queue.qsize())


def _worker_loop() -> None:
    while not _stop:
        run_id = _queue.get()
        set_run_queue_depth(_queue.qsize())
        if run_id < 0:
            return
        process_run_sync(run_id)


def process_run_sync(run_id: int) -> None:
    db = db_mod.SessionLocal()
    started_perf = datetime.now(timezone.utc)
    try:
        run = db.get(GovernanceRun, run_id)
        if run is None:
            return
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        db.add(
            AuditEvent(
                tenant_id=run.tenant_id,
                actor_user_id=run.requested_by_user_id,
                area="governance_run",
                action="started",
                entity_type="governance_run",
                entity_id=run.id,
                summary=f"Run {run.id} started",
            )
        )
        db.commit()

        settings = get_settings()
        # Resolve tenant correctly
        user_requested = db.get(User, run.requested_by_user_id)
        tenant_slug = (run.runtime_config_json or {}).get("tenant_slug")
        tenant = resolve_tenant_for_user(db, user_requested, tenant_slug) if user_requested else None
        
        settings_row_early = (
            db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
            if tenant
            else None
        )
        effective = resolve_effective_settings(db, settings, tenant)
        effective = apply_pipeline_overrides(effective, settings_row_early)
        provider_chain = resolve_provider_chain(db, tenant)
        if effective.guardrails_enabled and run.tenant_id:
            try:
                enforce_budget_cap(db, run.tenant_id, settings_row_early, effective)
            except GuardrailBlockedError as budget_exc:
                run.status = "failed"
                run.error_message = str(budget_exc)
                run.finished_at = datetime.now(timezone.utc)
                db.add(
                    AuditEvent(
                        tenant_id=run.tenant_id,
                        actor_user_id=run.requested_by_user_id,
                        area="guardrails",
                        action="budget_blocked",
                        entity_type="governance_run",
                        entity_id=run.id,
                        severity="warn",
                        summary=f"Run {run.id} blocked by {budget_exc.result.guard_name}",
                        after_json={"violations": [v.model_dump() for v in budget_exc.result.violations]},
                    )
                )
                db.commit()
                elapsed_ms = (datetime.now(timezone.utc) - started_perf).total_seconds() * 1000
                record_run(run.status, elapsed_ms, run.retry_count)
                return
        try:
            result = asyncio.run(run_governance(run.prompt, run.prompt_id, effective, llm_providers=provider_chain))
        except GuardrailBlockedError as guard_exc:
            run.status = "failed"
            run.error_message = str(guard_exc)
            run.finished_at = datetime.now(timezone.utc)
            db.add(
                AuditEvent(
                    tenant_id=run.tenant_id,
                    actor_user_id=run.requested_by_user_id,
                    area="guardrails",
                    action="blocked",
                    entity_type="governance_run",
                    entity_id=run.id,
                    severity="warn",
                    summary=f"Run {run.id} blocked by {guard_exc.result.guard_name}",
                    after_json={
                        "violations": [v.model_dump() for v in guard_exc.result.violations],
                    },
                )
            )
            db.commit()
            elapsed_ms = (datetime.now(timezone.utc) - started_perf).total_seconds() * 1000
            record_run(run.status, elapsed_ms, run.retry_count)
            return
        out = pipeline_result_to_jsonable(result)
        llm_cost = out.get("llm_cost") if isinstance(out.get("llm_cost"), dict) else {}
        for call in llm_cost.get("calls") or []:
            if not isinstance(call, dict):
                continue
            db.add(
                LLMCallLog(
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    agent_id=str(call.get("agent_id") or "unknown"),
                    provider_name=str(call.get("provider_name") or "unknown"),
                    model_name=str(call.get("model_name") or "unknown"),
                    prompt_tokens=int(call.get("prompt_tokens") or 0),
                    completion_tokens=int(call.get("completion_tokens") or 0),
                    cost_usd=float(call.get("cost_usd") or 0.0),
                    latency_ms=int(call.get("latency_ms") or 0),
                )
            )
        connector_rows = (
            db.execute(select(TenantConnectorConfig).where(TenantConnectorConfig.tenant_id == run.tenant_id))
            .scalars()
            .all()
            if run.tenant_id
            else []
        )
        integration_signals = {}
        for row in connector_rows:
            signal = connector_signal(row)
            integration_signals[row.connector_name] = signal
            status = "ok" if signal.get("freshness") != "degraded" else "error"
            record_connector_call(
                row.connector_name,
                status=status,
                latency_ms=float(signal.get("latency_ms") or 0),
                error_category=str(signal.get("error_category")) if signal.get("error_category") else None,
            )
        for row in connector_rows:
            row.telemetry_json = integration_signals[row.connector_name]
            row.last_sync_at = datetime.now(timezone.utc)
        settings_row = settings_row_early
        rag_cfg = settings_row.rag_config_json if settings_row else {}
        rag_docs = rag_cfg.get("documents", []) if isinstance(rag_cfg, dict) else []
        rag_context = rag_docs[:3] if isinstance(rag_docs, list) else []
        out["runtime_config"] = {
            "tenant_slug": tenant.slug if tenant else None,
            "connector_mode": effective.connector_mode.value,
            "github_repo": effective.github_repo,
            "ai": get_ai_runtime_summary(db, tenant),
            "rag": {"enabled": bool(rag_cfg.get("enabled")) if isinstance(rag_cfg, dict) else False, "doc_count": len(rag_docs) if isinstance(rag_docs, list) else 0},
        }
        out["integration_signals"] = integration_signals
        out["rag_context"] = rag_context

        findings, findings_llm_meta = build_agent_findings_with_llm(
            integration_signals,
            observability_snapshot(window_seconds=900),
            provider_chain,
        )
        consensus = compute_consensus(findings)
        incident = build_incident(findings, consensus)
        orch_snap = orchestration_snapshot_from_run_payload(out)
        ev_json = incident.get("evidence_json") if isinstance(incident.get("evidence_json"), dict) else {}
        incident["evidence_json"] = {**ev_json, "orchestration_snapshot": orch_snap}
        exec_summary = build_executive_summary(incident)
        ex_md = exec_summary.get("metadata_json") if isinstance(exec_summary.get("metadata_json"), dict) else {}
        exec_summary["metadata_json"] = {**ex_md, **orch_snap}
        explanation_meta = out.get("llm_invocation") if isinstance(out.get("llm_invocation"), dict) else {}
        out["agentic_intelligence"] = {
            "findings": findings,
            "consensus": consensus,
            "incident": incident,
            "executive_summary": exec_summary,
        }
        out["llm_invocation"] = {
            "status": "ok" if findings_llm_meta.get("status") == "ok" and explanation_meta.get("status") == "ok" else "degraded",
            "provider": explanation_meta.get("provider"),
            "model": explanation_meta.get("model"),
            "stages": {
                "agent_findings": findings_llm_meta,
                "explanation": explanation_meta if explanation_meta else {"status": "degraded", "reason": "no_active_provider"},
            },
        }
        record_llm_invocation(out["llm_invocation"]["status"])

        out = enrich_run_payload(out, db=db, tenant=tenant, settings=effective, ts_row=settings_row)

        run.result_json = out
        run.status = "succeeded"
        run.error_message = None
        run.finished_at = datetime.now(timezone.utc)
        db.add(
            AuditEvent(
                tenant_id=run.tenant_id,
                actor_user_id=run.requested_by_user_id,
                area="governance_run",
                action="succeeded",
                entity_type="governance_run",
                entity_id=run.id,
                summary=f"Run {run.id} completed",
                after_json={"status": run.status},
            )
        )
        evidence_by_connector = out.get("raw_evidence_by_connector") or {}
        if isinstance(evidence_by_connector, dict):
            for connector_name, payload in evidence_by_connector.items():
                db.add(
                    EvidenceSnapshot(
                        run_id=run.id,
                        connector_name=str(connector_name),
                        payload_json=payload if isinstance(payload, dict) else {"payload": payload},
                    )
                )
        for connector_name, payload in integration_signals.items():
            db.add(
                EvidenceSnapshot(
                    run_id=run.id,
                    connector_name=connector_name,
                    payload_json=payload,
                )
            )
        for f in findings:
            db.add(
                AgentFinding(
                    run_id=run.id,
                    tenant_id=run.tenant_id,
                    agent_name=f["agent_name"],
                    domain=f["domain"],
                    severity=f["severity"],
                    confidence=float(f["confidence"]),
                    summary=f["summary"],
                    evidence_json=f["evidence_json"],
                )
            )
        db.add(
            CorrelatedIncident(
                run_id=run.id,
                tenant_id=run.tenant_id,
                title=incident["title"],
                severity=incident["severity"],
                status=incident["status"],
                confidence=float(incident["confidence"]),
                consensus_score=float(incident["consensus_score"]),
                conflict_detected=bool(incident["conflict_detected"]),
                evidence_json=incident["evidence_json"],
                recommendation_json=incident["recommendation_json"],
            )
        )
        db.add(
            ExecutiveSummary(
                tenant_id=run.tenant_id,
                run_id=run.id,
                summary_type=exec_summary["summary_type"],
                title=exec_summary["title"],
                content=exec_summary["content"],
                xi_score=float(exec_summary["xi_score"]),
                metadata_json=exec_summary["metadata_json"],
            )
        )
        db.commit()
        elapsed_ms = (datetime.now(timezone.utc) - started_perf).total_seconds() * 1000
        record_run(run.status, elapsed_ms, run.retry_count)
        try:
            deliver_run_complete_notifications(run.id)
        except Exception:  # noqa: BLE001
            _log.exception("governance_delivery_failed", extra={"run_id": run.id})
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        run = db.get(GovernanceRun, run_id)
        if run is None:
            return
        run.retry_count += 1
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        if run.retry_count <= _MAX_RETRIES:
            run.status = "queued"
            db.commit()
            enqueue_run(run_id)
            elapsed_ms = (datetime.now(timezone.utc) - started_perf).total_seconds() * 1000
            record_run("retry", elapsed_ms, run.retry_count)
            return
        run.status = "failed"
        record_dead_letter()
        db.add(
            AuditEvent(
                tenant_id=run.tenant_id,
                actor_user_id=run.requested_by_user_id,
                area="governance_run",
                action="failed",
                entity_type="governance_run",
                entity_id=run.id,
                severity="error",
                summary=f"Run {run.id} failed: {run.error_message}",
            )
        )
        db.commit()
        elapsed_ms = (datetime.now(timezone.utc) - started_perf).total_seconds() * 1000
        record_run(run.status, elapsed_ms, run.retry_count)
    finally:
        db.close()


def list_recent_runs(limit: int = 100) -> list[GovernanceRun]:
    db = db_mod.SessionLocal()
    try:
        return db.execute(select(GovernanceRun).order_by(GovernanceRun.created_at.desc()).limit(limit)).scalars().all()
    finally:
        db.close()
