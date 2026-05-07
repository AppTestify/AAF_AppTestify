"""Single-page PDF summarizing decision framing + executive snapshot from a governance run."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def _safe_str(v: Any, max_len: int = 2000) -> str:
    if v is None:
        return "—"
    s = str(v).strip()
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s or "—"


def build_decision_framing_onepager_pdf(*, run_id: int, result_json: dict[str, Any] | None) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=f"Governance run {run_id}")
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph(f"<b>Governance decision framing — run #{run_id}</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    df = result_json.get("decision_framing") if isinstance(result_json, dict) else None
    orch = df.get("orchestration") if isinstance(df, dict) and isinstance(df.get("orchestration"), dict) else {}
    fs = df.get("findings_synthesis") if isinstance(df, dict) and isinstance(df.get("findings_synthesis"), dict) else {}

    story.append(Paragraph("<b>Orchestration path</b>", styles["Heading2"]))
    orch_lines = [
        f"consensus_score: {_safe_str(orch.get('consensus_score'), 80)}",
        f"recommended_action: {_safe_str(orch.get('recommended_action'), 500)}",
        f"utility_score: {_safe_str(orch.get('utility_score'), 80)}",
        f"xi_score: {_safe_str(orch.get('xi_score'), 80)}",
        f"rar_triggered: {_safe_str(orch.get('rar_triggered'), 80)}",
        f"rar_loops: {_safe_str(orch.get('rar_loops'), 80)}",
    ]
    story.append(Paragraph("<br/>".join(orch_lines), styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Findings synthesis</b>", styles["Heading2"]))
    fs_lines = [
        f"consensus_score: {_safe_str(fs.get('consensus_score'), 80)}",
        f"conflict_detected: {_safe_str(fs.get('conflict_detected'), 80)}",
        f"confidence: {_safe_str(fs.get('confidence'), 80)}",
    ]
    story.append(Paragraph("<br/>".join(fs_lines), styles["BodyText"]))
    story.append(Spacer(1, 10))

    ai = result_json.get("agentic_intelligence") if isinstance(result_json, dict) else None
    inc = ai.get("incident") if isinstance(ai, dict) and isinstance(ai.get("incident"), dict) else {}
    es = ai.get("executive_summary") if isinstance(ai, dict) and isinstance(ai.get("executive_summary"), dict) else {}

    story.append(Paragraph("<b>Incident (headline)</b>", styles["Heading2"]))
    story.append(Paragraph(_safe_str(inc.get("title"), 500), styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Executive summary</b>", styles["Heading2"]))
    story.append(Paragraph(_safe_str(es.get("title"), 500), styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(_safe_str(es.get("content"), 3500), styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()
