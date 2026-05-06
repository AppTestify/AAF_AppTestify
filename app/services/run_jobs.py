"""Background governance run worker (in-process queue for V1)."""

from __future__ import annotations

import asyncio
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
from app.models.tenant import Tenant
from app.services.agentic_intelligence import (
    build_agent_findings_with_llm,
    build_executive_summary,
    build_incident,
    compute_consensus,
)
from app.services.config_resolver import get_ai_runtime_summary, resolve_effective_settings
from app.services.governance_service import run_governance
from app.services.llm_runtime import resolve_provider_chain
from app.services.integration_signals import connector_signal
from app.services.observability import record_connector_call, record_dead_letter, record_llm_invocation, record_run, set_run_queue_depth
from app.services.observability import snapshot as observability_snapshot
from pm_interface.decision_formatter import pipeline_result_to_jsonable

_queue: "Queue[int]" = Queue()
_thread: Optional[Thread] = None
_lock = Lock()
_stop = False
_MAX_RETRIES = 2


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


def enqueue_run(run_id: int) -> None:
    _queue.put(run_id)
    set_run_queue_depth(_queue.qsize())


def _worker_loop() -> None:
    while not _stop:
        run_id = _queue.get()
        set_run_queue_depth(_queue.qsize())
        if run_id < 0:
            return
        _process_one(run_id)


def _process_one(run_id: int) -> None:
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
        tenant = db.get(Tenant, run.tenant_id) if run.tenant_id else None
        effective = resolve_effective_settings(db, settings, tenant)
        provider_chain = resolve_provider_chain(db, tenant)
        result = asyncio.run(run_governance(run.prompt, run.prompt_id, effective, llm_providers=provider_chain))
        out = pipeline_result_to_jsonable(result)
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
        settings_row = (
            db.execute(select(TenantSettings).where(TenantSettings.tenant_id == run.tenant_id)).scalar_one_or_none()
            if run.tenant_id
            else None
        )
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
        exec_summary = build_executive_summary(incident)
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
            _queue.put(run_id)
            set_run_queue_depth(_queue.qsize())
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
