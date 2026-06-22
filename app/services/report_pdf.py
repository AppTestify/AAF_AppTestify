"""PDF report builders (ReportLab tables)."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _header_story(title: str, subtitle: str | None = None) -> list[Any]:
    styles = getSampleStyleSheet()
    story: list[Any] = [Paragraph(f"<b>{title}</b>", styles["Title"])]
    if subtitle:
        story.append(Paragraph(subtitle, styles["Normal"]))
    story.append(Spacer(1, 12))
    return story


def _table_from_rows(rows: list[dict[str, Any]], max_cols: int = 8) -> Table | Paragraph:
    styles = getSampleStyleSheet()
    if not rows:
        return Paragraph("No data.", styles["BodyText"])
    headers = list(rows[0].keys())[:max_cols]
    data = [headers]
    for row in rows[:100]:
        data.append([str(row.get(h, ""))[:80] for h in headers])
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def build_runs_summary_pdf(
    rows: list[dict[str, Any]],
    *,
    exported_at: str | None = None,
    tenant_label: str = "",
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Governance run summary")
    generated = exported_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prefix = f"{tenant_label} · " if tenant_label else ""
    subtitle = f"{prefix}Generated {generated} · {len(rows)} runs"
    story = _header_story("Governance run summary", subtitle)
    story.append(_table_from_rows(rows))
    doc.build(story)
    return buf.getvalue()


def build_audit_events_pdf(
    rows: list[dict[str, Any]],
    *,
    exported_at: str | None = None,
    tenant_label: str = "",
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Audit events")
    generated = exported_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prefix = f"{tenant_label} · " if tenant_label else ""
    subtitle = f"{prefix}Generated {generated} · {len(rows)} events"
    story = _header_story("Audit events export", subtitle)
    story.append(_table_from_rows(rows))
    doc.build(story)
    return buf.getvalue()


def build_portfolio_executive_pdf(report: dict[str, Any], *, tenant_label: str = "") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Executive portfolio")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subtitle = f"{tenant_label} · Generated {generated}"
    story = _header_story("Executive portfolio report", subtitle)
    kpis = [
        ["Metric", "Value"],
        ["Projects total", report.get("projects_total", 0)],
        ["Active projects", report.get("active_projects", 0)],
        ["Releases total", report.get("releases_total", 0)],
        ["Approved", report.get("releases_approved", 0)],
        ["Blocked", report.get("releases_blocked", 0)],
        ["High risk open", report.get("high_risk_open", 0)],
    ]
    table = Table(kpis)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey)]))
    story.append(table)
    doc.build(story)
    return buf.getvalue()


def build_compliance_pdf(controls: list[dict[str, str]], title: str = "Compliance Report", exported_at: str | None = None) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=title)
    generated = exported_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subtitle = f"Generated {generated}"
    story = _header_story(title, subtitle)
    story.append(_table_from_rows(controls, max_cols=3))
    doc.build(story)
    return buf.getvalue()
