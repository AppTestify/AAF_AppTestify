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
from app.models.tenant import Tenant
from app.services.config_resolver import get_ai_runtime_summary, resolve_effective_settings
from app.services.governance_service import run_governance
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


def _worker_loop() -> None:
    while not _stop:
        run_id = _queue.get()
        if run_id < 0:
            return
        _process_one(run_id)


def _process_one(run_id: int) -> None:
    db = db_mod.SessionLocal()
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
        result = asyncio.run(run_governance(run.prompt, run.prompt_id, effective))
        out = pipeline_result_to_jsonable(result)
        out["runtime_config"] = {
            "tenant_slug": tenant.slug if tenant else None,
            "connector_mode": effective.connector_mode.value,
            "github_repo": effective.github_repo,
            "ai": get_ai_runtime_summary(db, tenant),
        }
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
        db.commit()
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
            return
        run.status = "failed"
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
    finally:
        db.close()


def list_recent_runs(limit: int = 100) -> list[GovernanceRun]:
    db = db_mod.SessionLocal()
    try:
        return db.execute(select(GovernanceRun).order_by(GovernanceRun.created_at.desc()).limit(limit)).scalars().all()
    finally:
        db.close()
