"""Shared async Jira API client for PM tools."""

from __future__ import annotations

from typing import Any

import httpx

from tools.context import ToolContext


def _auth(ctx: ToolContext) -> tuple[str, str] | None:
    if not ctx.jira_url or not ctx.jira_email or not ctx.jira_api_token:
        return None
    return (ctx.jira_email, ctx.jira_api_token)


async def jira_get(ctx: ToolContext, path: str, *, params: dict[str, Any] | None = None) -> Any:
    auth = _auth(ctx)
    if auth is None:
        return None
    url = f"{ctx.jira_url.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, auth=auth, params=params or {})
        if resp.status_code not in (200, 201):
            return None
        return resp.json()


async def jira_post(ctx: ToolContext, path: str, payload: dict[str, Any]) -> Any:
    auth = _auth(ctx)
    if auth is None:
        return None
    url = f"{ctx.jira_url.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(url, auth=auth, json=payload)
        if resp.status_code not in (200, 201):
            return None
        return resp.json()
