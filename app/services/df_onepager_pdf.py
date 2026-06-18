"""Single-page PDF summarizing decision framing + executive snapshot from a governance run."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


import re

def _safe_str(v: Any, max_len: int = 4000) -> str:
    if v is None:
        return "—"
    s = str(v).strip()
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s or "—"

def _markdown_to_reportlab(text: str) -> str:
    if not text:
        return "—"
    s = str(text)
    s = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', s)
    s = re.sub(r'^##\s+(.*)', r'<br/><b>\1</b>', s, flags=re.MULTILINE)
    s = re.sub(r'^\s*-\s+(.*)', r'&bull; \1', s, flags=re.MULTILINE)
    s = s.replace('\n', '<br/>')
    return s

def _color_score(val: Any) -> str:
    if val is None:
        return "—"
    try:
        f = float(val)
        color = "green" if f >= 0.70 else ("red" if f < 0.40 else "orange")
        return f'<font color="{color}"><b>{f:.2f}</b></font>'
    except (ValueError, TypeError):
        return str(val)

def _color_action(val: Any) -> str:
    if not val:
        return "—"
    s = str(val).lower()
    color = "green" if ("release" in s or "approve" in s) and "hold" not in s and "block" not in s else ("red" if "hold" in s or "block" in s or "rollback" in s else "orange")
    return f'<font color="{color}"><b>{val}</b></font>'


def build_decision_framing_onepager_pdf(*, run_id: int, result_json: dict[str, Any] | None, prompt: str | None = None) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title=f"Governance run {run_id}")
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.append(Paragraph(f"<b>Governance decision framing — run #{run_id}</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    if prompt:
        story.append(Paragraph("<b>Prompt</b>", styles["Heading2"]))
        story.append(Paragraph(_safe_str(prompt, 2000), styles["BodyText"]))
        story.append(Spacer(1, 10))

    df = result_json.get("decision_framing") if isinstance(result_json, dict) else None
    orch = df.get("orchestration") if isinstance(df, dict) and isinstance(df.get("orchestration"), dict) else {}
    fs = df.get("findings_synthesis") if isinstance(df, dict) and isinstance(df.get("findings_synthesis"), dict) else {}

    # Fallbacks for new structure
    consensus = result_json.get("consensus") if isinstance(result_json, dict) and isinstance(result_json.get("consensus"), dict) else {}
    rar = result_json.get("rar") if isinstance(result_json, dict) and isinstance(result_json.get("rar"), dict) else {}
    util = result_json.get("utility") if isinstance(result_json, dict) and isinstance(result_json.get("utility"), dict) else {}
    xi = result_json.get("explainability") if isinstance(result_json, dict) and isinstance(result_json.get("explainability"), dict) else {}

    orch_consensus = orch.get("consensus_score") if orch.get("consensus_score") is not None else consensus.get("consensus_score")
    rec_action = orch.get("recommended_action") if orch.get("recommended_action") is not None else util.get("recommended_action")
    util_score = orch.get("utility_score") if orch.get("utility_score") is not None else util.get("utility_score")
    xi_score = orch.get("xi_score") if orch.get("xi_score") is not None else xi.get("xi_score")
    rar_triggered = orch.get("rar_triggered") if orch.get("rar_triggered") is not None else rar.get("rar_triggered")
    rar_loops = orch.get("rar_loops") if orch.get("rar_loops") is not None else rar.get("rar_loops")

    story.append(Paragraph("<b>Orchestration path</b>", styles["Heading2"]))
    orch_lines = [
        f"<b>consensus_score:</b> {_color_score(orch_consensus)}",
        f"<b>recommended_action:</b> {_color_action(rec_action)}",
        f"<b>utility_score:</b> {_color_score(util_score)}",
        f"<b>xi_score:</b> {_color_score(xi_score)}",
        f"<b>rar_triggered:</b> {_safe_str(rar_triggered, 80)}",
        f"<b>rar_loops:</b> {_safe_str(rar_loops, 80)}",
    ]
    story.append(Paragraph("<br/>".join(orch_lines), styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Findings synthesis</b>", styles["Heading2"]))
    
    fs_consensus = fs.get("consensus_score") if fs.get("consensus_score") is not None else consensus.get("consensus_score")
    fs_conflict = fs.get("conflict_detected") if fs.get("conflict_detected") is not None else consensus.get("conflict_detected")
    fs_confidence = fs.get("confidence") if fs.get("confidence") is not None else consensus.get("confidence")

    fs_lines = [
        f"<b>consensus_score:</b> {_color_score(fs_consensus)}",
        f"<b>conflict_detected:</b> {_safe_str(fs_conflict, 80)}",
        f"<b>confidence:</b> {_color_score(fs_confidence)}",
    ]
    story.append(Paragraph("<br/>".join(fs_lines), styles["BodyText"]))
    story.append(Spacer(1, 10))

    ai = result_json.get("agentic_intelligence") if isinstance(result_json, dict) else None
    inc = ai.get("incident") if isinstance(ai, dict) and isinstance(ai.get("incident"), dict) else {}
    es = ai.get("executive_summary") if isinstance(ai, dict) and isinstance(ai.get("executive_summary"), dict) else {}

    pm_view = result_json.get("pm_view") if isinstance(result_json, dict) and isinstance(result_json.get("pm_view"), dict) else {}
    
    inc_title = inc.get("title") if inc.get("title") else pm_view.get("headline")
    es_title = es.get("title") if es.get("title") else pm_view.get("subtitle")
    
    es_content = es.get("content")
    if not es_content:
        es_content = result_json.get("explanation") if isinstance(result_json, dict) and isinstance(result_json.get("explanation"), str) else None

    story.append(Paragraph("<b>Incident (headline)</b>", styles["Heading2"]))
    story.append(Paragraph(_markdown_to_reportlab(_safe_str(inc_title, 1000)), styles["BodyText"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Executive summary</b>", styles["Heading2"]))
    story.append(Paragraph(_markdown_to_reportlab(_safe_str(es_title, 1000)), styles["BodyText"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(_markdown_to_reportlab(_safe_str(es_content, 5000)), styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()
