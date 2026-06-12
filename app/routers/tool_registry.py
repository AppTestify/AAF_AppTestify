"""Agent tool registry API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter

from agents.tool_registry import filter_registry

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/tool-registry")
def get_tool_registry(
    agent: Optional[str] = None,
    status: Optional[str] = None,
    method: Optional[str] = None,
):
    """Return canonical tool registry for UI, docs, and marketing."""
    return filter_registry(agent=agent, status=status, method=method).model_dump()
