"""Webhook ingestion for real-time tool signal refresh."""

from __future__ import annotations  # noqa: I001

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request

from aaf.config import get_settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
_log = logging.getLogger("aaf.webhooks")

# In-memory cache invalidated on workflow_run events (per-process; use Redis in multi-replica prod)
_ci_cache_invalidation: dict[str, str] = {}


def get_ci_cache_token(repo: str) -> Optional[str]:
    return _ci_cache_invalidation.get(repo)


@router.post("/github/workflow_run")
async def github_workflow_run(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(default=None),
    x_github_event: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """
    GitHub workflow_run webhook — invalidates CI tool cache for the repo.
    Configure in GitHub: Settings → Webhooks → workflow_run events.
    """
    body = await request.body()
    settings = get_settings()

    if settings.github_token and x_hub_signature_256:
        secret = settings.github_token.encode()
        expected = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, x_hub_signature_256):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    if x_github_event and x_github_event != "workflow_run":
        return {"status": "ignored", "event": x_github_event}

    repo_full = (payload.get("repository") or {}).get("full_name", "")
    run = payload.get("workflow_run") or {}
    if repo_full:
        _ci_cache_invalidation[repo_full] = datetime.now(timezone.utc).isoformat()
        _log.info("CI cache invalidated for %s (workflow_run %s)", repo_full, run.get("id"))

    return {
        "status": "ok",
        "repo": repo_full,
        "workflow_run_id": run.get("id"),
        "conclusion": run.get("conclusion"),
        "cache_invalidated_at": _ci_cache_invalidation.get(repo_full),
    }
