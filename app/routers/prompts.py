"""Prompt library."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/prompts", tags=["prompts"])

_ROOT = Path(__file__).resolve().parents[2]
_LIBRARY_PATH = _ROOT / "data" / "prompt_library.json"


@router.get("/library")
def prompt_library():
    data = json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))
    return data
