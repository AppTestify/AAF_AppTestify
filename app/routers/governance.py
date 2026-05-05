"""Governance API routes."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from aaf.config import Settings
from app.deps import settings_dep
from app.services.governance_service import run_governance
from pm_interface.decision_formatter import pipeline_result_to_jsonable

router = APIRouter(prefix="/governance", tags=["governance"])

_ROOT = Path(__file__).resolve().parents[2]
_LIBRARY_PATH = _ROOT / "data" / "prompt_library.json"


class RunBody(BaseModel):
    prompt: str = Field(min_length=1)
    prompt_id: str | None = None


@router.post("/run")
async def governance_run(body: RunBody, settings: Settings = Depends(settings_dep)):
    result = await run_governance(body.prompt, body.prompt_id, settings)
    return pipeline_result_to_jsonable(result)


@router.post("/batch")
async def governance_batch(settings: Settings = Depends(settings_dep)):
    data = json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))
    prompts = data.get("prompts") or []
    results: list[dict] = []
    for p in prompts:
        text = p.get("text") or ""
        pid = p.get("id")
        r = await run_governance(text, pid, settings)
        results.append(
            {
                "prompt_id": pid,
                "consensus": r.consensus.consensus_score,
                "rar_triggered": r.rar.rar_triggered,
                "recommended_action": r.utility.recommended_action.value,
                "xi": r.explainability.xi_score,
            }
        )
    return {"runs": results, "count": len(results)}
