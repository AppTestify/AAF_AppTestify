"""Shared async GitHub API client for tools."""

from __future__ import annotations

from typing import Any

import httpx

from tools.context import ToolContext


def _headers(ctx: ToolContext) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if ctx.github_token:
        headers["Authorization"] = f"Bearer {ctx.github_token}"
    return headers


def _repo_parts(ctx: ToolContext) -> tuple[str, str] | None:
    if "/" not in ctx.github_repo:
        return None
    owner, name = ctx.github_repo.split("/", 1)
    return owner, name


async def github_get(ctx: ToolContext, path: str, *, params: dict[str, Any] | None = None) -> Any:
    parts = _repo_parts(ctx)
    if parts is None:
        return None
    owner, name = parts
    url = f"https://api.github.com/repos/{owner}/{name}{path}"
    async with httpx.AsyncClient(timeout=15.0, headers=_headers(ctx)) as client:
        resp = await client.get(url, params=params or {})
        if resp.status_code != 200:
            return None
        return resp.json()
