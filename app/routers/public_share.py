"""Unauthenticated signed-URL access to governance run snapshots."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.governance import GovernanceRun
from app.services.df_onepager_pdf import build_decision_framing_onepager_pdf
from app.services.share_link import decode_governance_share_token

router = APIRouter(prefix="/public", tags=["public-share"])


def _load_run_for_token(db: Session, token: str) -> GovernanceRun:
    try:
        claims = decode_governance_share_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    run = db.get(GovernanceRun, int(claims["run_id"]))
    if run is None or run.tenant_id != int(claims["tid"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if run.status != "succeeded" or not run.result_json:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run snapshot is not available")
    return run


@router.get("/share/{token}", response_class=HTMLResponse)
def public_share_page(token: str, db: Session = Depends(get_db)):
    run = _load_run_for_token(db, token)
    rj = run.result_json if isinstance(run.result_json, dict) else {}
    df = rj.get("decision_framing") if isinstance(rj.get("decision_framing"), dict) else {}
    orch = df.get("orchestration") if isinstance(df.get("orchestration"), dict) else {}
    ai = rj.get("agentic_intelligence") if isinstance(rj.get("agentic_intelligence"), dict) else {}
    inc = ai.get("incident") if isinstance(ai.get("incident"), dict) else {}
    es = ai.get("executive_summary") if isinstance(ai.get("executive_summary"), dict) else {}

    def esc(s: object) -> str:
        return (
            str(s if s is not None else "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    pdf_href = "onepager.pdf"
    finished = run.finished_at.isoformat() if run.finished_at else "—"
    body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Run {run.id}</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 52rem; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
h1 {{ font-size: 1.35rem; }}
.meta {{ color: #555; font-size: 0.9rem; margin-bottom: 1.5rem; }}
.grid {{ display: grid; gap: 1rem; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; background: #fafafa; }}
a {{ color: #0b5fff; }}
</style></head><body>
<h1>Governance run #{run.id}</h1>
<p class="meta">Finished (UTC): {esc(finished)} · <a href="{esc(pdf_href)}">Download DF one-pager (PDF)</a></p>
<div class="grid">
<div class="card"><strong>Prompt</strong><p>{esc(run.prompt[:2000])}</p></div>
<div class="card"><strong>Orchestration</strong>
<p>Recommended action: {esc(orch.get("recommended_action"))}</p>
<p>Consensus: {esc(orch.get("consensus_score"))} · Utility: {esc(orch.get("utility_score"))} · Xi: {esc(orch.get("xi_score"))}</p>
</div>
<div class="card"><strong>Incident</strong><p>{esc(inc.get("title"))}</p></div>
<div class="card"><strong>Executive summary</strong><p><b>{esc(es.get("title"))}</b></p><p>{esc(es.get("content"))}</p></div>
</div>
</body></html>"""
    return HTMLResponse(content=body)


@router.get("/share/{token}/onepager.pdf")
def public_share_onepager_pdf(token: str, db: Session = Depends(get_db)):
    run = _load_run_for_token(db, token)
    rj = run.result_json if isinstance(run.result_json, dict) else {}
    pdf = build_decision_framing_onepager_pdf(run_id=run.id, result_json=rj)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="governance_run_{run.id}_df_onepager.pdf"'},
    )
