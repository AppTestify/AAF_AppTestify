"""Export/report endpoints for governance runs and audit events."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_active_user, require_permission
from app.models.governance import AuditEvent, GovernanceRun
from app.models.tenant import Tenant
from app.routers.portfolio import build_executive_portfolio_report
from app.services.df_onepager_pdf import build_decision_framing_onepager_pdf
from app.services.email_runtime import send_resolved_email_with_attachments
from app.services.report_pdf import build_audit_events_pdf, build_portfolio_executive_pdf, build_runs_summary_pdf, build_compliance_pdf
from app.services.report_xlsx import build_audit_events_xlsx, build_portfolio_executive_xlsx, build_runs_summary_xlsx
from app.services.smtp_resolver import resolve_smtp_dataclass
from app.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])

_EXPORT_FORMAT_PATTERN = "^(json|csv|xlsx|pdf)$"

# Column order for empty CSV (no rows)
_RUN_SUMMARY_CSV_FIELDS = [
    "run_id",
    "tenant_id",
    "portfolio_project_id",
    "status",
    "prompt_id",
    "prompt",
    "orchestration_consensus_score",
    "findings_consensus_score",
    "findings_conflict_detected",
    "recommended_action",
    "utility_score",
    "xi_score",
    "rar_triggered",
    "rar_loops",
    "primary_recommendation_source",
    "created_at",
    "finished_at",
]


def _flatten_run_for_export(r: GovernanceRun) -> dict[str, Any]:
    """Normalized columns for CSV/JSON summaries (orchestration vs findings when present)."""
    result = r.result_json if isinstance(r.result_json, dict) else {}
    df = result.get("decision_framing") if isinstance(result.get("decision_framing"), dict) else {}
    orch = df.get("orchestration") if isinstance(df.get("orchestration"), dict) else {}
    fsyn = df.get("findings_synthesis") if isinstance(df.get("findings_synthesis"), dict) else {}
    consensus = result.get("consensus") if isinstance(result.get("consensus"), dict) else {}
    rar = result.get("rar") if isinstance(result.get("rar"), dict) else {}
    util = result.get("utility") if isinstance(result.get("utility"), dict) else {}
    xi = result.get("explainability") if isinstance(result.get("explainability"), dict) else {}

    orch_consensus = orch.get("consensus_score")
    if orch_consensus is None:
        orch_consensus = consensus.get("consensus_score")

    rec_action = orch.get("recommended_action") if orch else None
    if rec_action is None:
        rec_action = util.get("recommended_action")

    return {
        "run_id": r.id,
        "tenant_id": r.tenant_id,
        "portfolio_project_id": r.portfolio_project_id,
        "status": r.status,
        "prompt_id": r.prompt_id,
        "prompt": r.prompt,
        "orchestration_consensus_score": orch_consensus,
        "findings_consensus_score": fsyn.get("consensus_score"),
        "findings_conflict_detected": fsyn.get("conflict_detected"),
        "recommended_action": rec_action,
        "utility_score": orch.get("utility_score") if orch.get("utility_score") is not None else util.get("utility_score"),
        "xi_score": orch.get("xi_score") if orch.get("xi_score") is not None else xi.get("xi_score"),
        "rar_triggered": rar.get("rar_triggered"),
        "rar_loops": rar.get("rar_loops"),
        "primary_recommendation_source": df.get("primary_recommendation_source"),
        "created_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


def _executive_run_bundle(run: GovernanceRun) -> dict[str, Any]:
    """Shareable governance snapshot (tenant-scoped auth required)."""
    result = run.result_json if isinstance(run.result_json, dict) else {}
    return {
        "run_id": run.id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": run.tenant_id,
        "portfolio_project_id": run.portfolio_project_id,
        "prompt": run.prompt,
        "prompt_id": run.prompt_id,
        "status": run.status,
        "created_at": run.created_at.isoformat() if isinstance(run.created_at, datetime) else str(run.created_at),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "decision_framing": result.get("decision_framing"),
        "consensus": result.get("consensus"),
        "rar": result.get("rar"),
        "utility": result.get("utility"),
        "explainability": result.get("explainability"),
        "pm_view": result.get("pm_view"),
        "explanation": result.get("explanation"),
        "agentic_intelligence": result.get("agentic_intelligence"),
    }


def _scoped_runs_query(current: User):
    q = select(GovernanceRun).order_by(GovernanceRun.created_at.desc())
    if not current.is_superadmin:
        q = q.where(GovernanceRun.tenant_id == current.tenant_id)
    return q


def _scoped_audit_query(current: User):
    q = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if not current.is_superadmin:
        q = q.where(AuditEvent.tenant_id == current.tenant_id)
    return q


def _audit_payload(rows: list[AuditEvent]) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id,
            "tenant_id": r.tenant_id,
            "actor_user_id": r.actor_user_id,
            "area": r.area,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "severity": r.severity,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
            "before_json": json.dumps(r.before_json) if r.before_json is not None else "",
            "after_json": json.dumps(r.after_json) if r.after_json is not None else "",
        }
        for r in rows
    ]


def _tenant_label(current: User) -> str:
    if current.is_superadmin:
        return "Platform (all tenants)"
    return f"Tenant {current.tenant_id}"


def _binary_response(content: bytes, *, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/runs/{run_id}/export")
def export_single_run(
    run_id: int,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("runs.create")),
):
    """Download one run's executive governance snapshot for sharing (auth required)."""
    row = db.get(GovernanceRun, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not current.is_superadmin and current.tenant_id != row.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed for this run")

    bundle = _executive_run_bundle(row)
    flat = _flatten_run_for_export(row)

    if format == "json":
        return {"format_version": 1, "summary_columns": flat, "executive_bundle": bundle}

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(flat.keys()))
    writer.writeheader()
    writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in flat.items()})
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="governance_run_{run_id}.csv"'},
    )


@router.get("/runs/summary")
def runs_summary(
    format: str = Query(default="json", pattern=_EXPORT_FORMAT_PATTERN),
    status: Optional[str] = Query(default=None),
    portfolio_project_id: Optional[int] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("runs.create")),
):
    q = _scoped_runs_query(current)
    if status:
        q = q.where(GovernanceRun.status == status)
    if portfolio_project_id is not None:
        q = q.where(GovernanceRun.portfolio_project_id == portfolio_project_id)
    rows = db.execute(q.limit(limit)).scalars().all()
    payload = [_flatten_run_for_export(r) for r in rows]
    exported_at = datetime.now(timezone.utc).isoformat()

    if format == "json":
        return {"count": len(payload), "items": payload, "exported_at": exported_at}

    if format == "xlsx":
        content = build_runs_summary_xlsx(payload)
        return _binary_response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="governance_run_summary.xlsx",
        )

    if format == "pdf":
        content = build_runs_summary_pdf(payload, tenant_label=_tenant_label(current))
        return _binary_response(content, media_type="application/pdf", filename="governance_run_summary.pdf")

    buf = io.StringIO()
    fnames = list(payload[0].keys()) if payload else _RUN_SUMMARY_CSV_FIELDS
    writer = csv.DictWriter(buf, fieldnames=fnames)
    writer.writeheader()
    for row in payload:
        safe = {
            k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
            for k, v in row.items()
        }
        writer.writerow(safe)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="governance_run_summary.csv"'},
    )


@router.get("/audit-events")
def audit_events_export(
    format: str = Query(default="json", pattern=_EXPORT_FORMAT_PATTERN),
    area: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=10000),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    q = _scoped_audit_query(current)
    if area:
        q = q.where(AuditEvent.area == area)
    rows = db.execute(q.limit(limit)).scalars().all()
    payload = _audit_payload(rows)
    exported_at = datetime.now(timezone.utc).isoformat()

    if format == "json":
        json_items = [
            {
                **row,
                "before_json": json.loads(row["before_json"]) if row["before_json"] else None,
                "after_json": json.loads(row["after_json"]) if row["after_json"] else None,
            }
            for row in payload
        ]
        return {"count": len(json_items), "items": json_items, "exported_at": exported_at}

    if format == "xlsx":
        content = build_audit_events_xlsx(payload)
        return _binary_response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="audit_events.xlsx",
        )

    if format == "pdf":
        content = build_audit_events_pdf(payload, tenant_label=_tenant_label(current))
        return _binary_response(content, media_type="application/pdf", filename="audit_events.pdf")

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "id",
            "tenant_id",
            "actor_user_id",
            "area",
            "action",
            "entity_type",
            "entity_id",
            "severity",
            "summary",
            "created_at",
            "before_json",
            "after_json",
        ],
    )
    writer.writeheader()
    for row in payload:
        writer.writerow(row)
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit_events.csv"'},
    )


class ReportEmailIn(BaseModel):
    report_type: str = Field(pattern="^(runs_summary|audit_events|portfolio_executive)$")
    format: str = Field(pattern="^(xlsx|pdf)$")
    recipients: list[str] = Field(min_length=1)
    status: Optional[str] = None
    area: Optional[str] = None
    limit: int = Field(default=200, ge=1, le=5000)


def _build_report_attachment(
    *,
    report_type: str,
    fmt: str,
    db: Session,
    current: User,
    status: Optional[str],
    area: Optional[str],
    limit: int,
) -> tuple[bytes, str, str]:
    exported_at = datetime.now(timezone.utc).isoformat()
    tenant_label = ""
    if current.tenant_id:
        tenant = db.get(Tenant, current.tenant_id)
        if tenant:
            tenant_label = tenant.slug

    if report_type == "runs_summary":
        q = _scoped_runs_query(current)
        if status:
            q = q.where(GovernanceRun.status == status)
        rows = db.execute(q.limit(limit)).scalars().all()
        payload = [_flatten_run_for_export(r) for r in rows]
        if fmt == "xlsx":
            return (
                build_runs_summary_xlsx(payload),
                "governance_run_summary.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        return (
            build_runs_summary_pdf(payload, exported_at=exported_at, tenant_label=tenant_label),
            "governance_run_summary.pdf",
            "application/pdf",
        )

    if report_type == "audit_events":
        q = _scoped_audit_query(current)
        if area:
            q = q.where(AuditEvent.area == area)
        rows = db.execute(q.limit(limit)).scalars().all()
        payload = _audit_payload(rows)
        if fmt == "xlsx":
            return (
                build_audit_events_xlsx(payload),
                "audit_events.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        return (
            build_audit_events_pdf(payload, exported_at=exported_at, tenant_label=tenant_label),
            "audit_events.pdf",
            "application/pdf",
        )

    report = build_executive_portfolio_report(db, current)
    payload = report.model_dump()
    payload["exported_at"] = exported_at
    if fmt == "xlsx":
        return (
            build_portfolio_executive_xlsx(payload),
            "portfolio_executive.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return (
        build_portfolio_executive_pdf(payload, tenant_label=tenant_label),
        "portfolio_executive.pdf",
        "application/pdf",
    )


@router.post("/email")
def email_report(
    body: ReportEmailIn,
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    tenant_id = current.tenant_id
    if tenant_id is None and not current.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant scope required")

    smtp = resolve_smtp_dataclass(db, tenant_id)
    if not smtp.is_configured:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="SMTP is not configured")

    content, filename, mime = _build_report_attachment(
        report_type=body.report_type,
        fmt=body.format,
        db=db,
        current=current,
        status=body.status,
        area=body.area,
        limit=body.limit,
    )
    recipients = [e.strip().lower() for e in body.recipients if e.strip()]
    if not recipients:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid recipients")

    send_resolved_email_with_attachments(
        smtp,
        to_emails=recipients,
        subject=f"Report: {body.report_type}",
        body=f"Attached {body.report_type} report ({body.format}).",
        attachments=[(filename, content, mime)],
        template_key="report_on_demand",
        template_values={
            "report_type": body.report_type.replace("_", " "),
            "format": body.format.upper(),
        },
    )
    return {"ok": True, "sent_to": recipients, "attachment": filename}


@router.get("/portfolio/executive")
def portfolio_executive_export(
    format: str = Query(default="json", pattern="^(json|xlsx|pdf)$"),
    db: Session = Depends(get_db),
    current: User = Depends(require_permission("cases.manage")),
):
    report = build_executive_portfolio_report(db, current)
    payload = report.model_dump()
    payload["exported_at"] = datetime.now(timezone.utc).isoformat()

    if format == "json":
        return payload

    if format == "xlsx":
        content = build_portfolio_executive_xlsx(payload)
        return _binary_response(
            content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="portfolio_executive.xlsx",
        )

    content = build_portfolio_executive_pdf(payload, tenant_label=_tenant_label(current))
    return _binary_response(content, media_type="application/pdf", filename="portfolio_executive.pdf")


@router.get("/pdf/{run_id}")
def export_run_pdf(
    run_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    run = db.get(GovernanceRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    if not user.is_superadmin and user.tenant_id != run.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    result_json = run.result_json if isinstance(run.result_json, dict) else {}
    pdf_bytes = build_decision_framing_onepager_pdf(run_id=run.id, result_json=result_json, prompt=run.prompt)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="governance_run_{run_id}.pdf"'},
    )


@router.get("/compliance")
def compliance_export(
    framework: str = Query(default="soc2"),
    format: str = Query(default="json", pattern="^(json|pdf)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """SOC2-oriented compliance control mapping export."""
    del db, user
    from pathlib import Path
    
    docs_dir = Path(__file__).parent.parent.parent / "docs" / "compliance"
    mapping_file = docs_dir / "control-mapping.md"
    
    controls = []
    if mapping_file.exists():
        lines = mapping_file.read_text(encoding="utf-8").splitlines()
        in_table = False
        for line in lines:
            line = line.strip()
            if line.startswith("|") and "Control Area" in line and "Evidence Artifact" in line:
                in_table = True
                continue
            if in_table and line.startswith("| ---"):
                continue
            if in_table and line.startswith("|"):
                parts = [p.strip() for p in line.strip("|").split("|")]
                if len(parts) >= 3:
                    controls.append({
                        "Control Area": parts[0],
                        "Implementation Reference": parts[1],
                        "Evidence Artifact": parts[2],
                    })
            elif in_table and not line.strip():
                in_table = False
                
    generated_at = datetime.now(timezone.utc).isoformat()
    
    if format == "pdf":
        pdf_bytes = build_compliance_pdf(
            controls, 
            title=f"{framework.upper()} Compliance Report",
            exported_at=generated_at
        )
        return _binary_response(
            pdf_bytes,
            media_type="application/pdf",
            filename=f"{framework}_compliance_report.pdf"
        )
        
    return {
        "framework": framework,
        "generated_at": generated_at,
        "controls": controls,
    }
