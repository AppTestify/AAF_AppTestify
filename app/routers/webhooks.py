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

# In-memory fallback when Redis is not configured (single-process dev)
_ci_cache_invalidation: dict[str, str] = {}
_CI_CACHE_TTL_SECONDS = 3600


def _redis_ci_key(key: str) -> str:
    return f"aaf:ci:invalidated:{key}"


def invalidate_ci_cache(key: str) -> str:
    ts = datetime.now(timezone.utc).isoformat()
    from app.services.redis_client import get_redis_client

    client = get_redis_client()
    if client is not None:
        try:
            client.set(_redis_ci_key(key), ts, ex=_CI_CACHE_TTL_SECONDS)
            return ts
        except Exception:  # noqa: BLE001
            _log.exception("redis_ci_cache_invalidate_failed", extra={"key": key})
    _ci_cache_invalidation[key] = ts
    return ts


def get_ci_cache_token(repo: str) -> Optional[str]:
    from app.services.redis_client import get_redis_client

    client = get_redis_client()
    if client is not None:
        try:
            val = client.get(_redis_ci_key(repo))
            if val:
                return str(val)
        except Exception:  # noqa: BLE001
            _log.exception("redis_ci_cache_read_failed", extra={"key": repo})
    return _ci_cache_invalidation.get(repo)


def _github_webhook_secret() -> str:
    settings = get_settings()
    return (settings.github_webhook_secret or settings.github_token or "").strip()


def _verify_github_signature(body: bytes, signature: Optional[str]) -> None:
    secret = _github_webhook_secret()
    if signature:
        if not secret:
            raise HTTPException(status_code=401, detail="Webhook signature present but secret not configured")
        expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    elif secret:
        raise HTTPException(status_code=401, detail="Missing webhook signature")


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
    _verify_github_signature(body, x_hub_signature_256)

    try:
        import json

        payload = json.loads(body.decode())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    if x_github_event and x_github_event != "workflow_run":
        return {"status": "ignored", "event": x_github_event}

    from app.services.kafka_producer import kafka_enabled, publish_webhook_event

    if kafka_enabled():
        publish_webhook_event("github", "github.workflow_run", payload)
        repo_full = (payload.get("repository") or {}).get("full_name", "")
        run = payload.get("workflow_run") or {}
        return {
            "status": "accepted",
            "queued": True,
            "repo": repo_full,
            "workflow_run_id": run.get("id"),
        }

    repo_full = (payload.get("repository") or {}).get("full_name", "")
    run = payload.get("workflow_run") or {}
    invalidated_at = None
    if repo_full:
        invalidated_at = invalidate_ci_cache(repo_full)
        _log.info("CI cache invalidated for %s (workflow_run %s)", repo_full, run.get("id"))

    return {
        "status": "ok",
        "repo": repo_full,
        "workflow_run_id": run.get("id"),
        "conclusion": run.get("conclusion"),
        "cache_invalidated_at": invalidated_at,
    }


@router.post("/jira")
async def jira_webhook(request: Request) -> dict[str, Any]:
    """Jira issue_updated webhook — invalidates PM tool caches."""
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    from app.services.kafka_producer import kafka_enabled, publish_webhook_event

    if kafka_enabled():
        publish_webhook_event("jira", "jira.issue_updated", payload)
        key = (payload.get("issue") or {}).get("key", "")
        return {"status": "accepted", "queued": True, "issue_key": key}

    issue = payload.get("issue") or {}
    key = issue.get("key", "")
    invalidated_at = None
    if key:
        invalidated_at = invalidate_ci_cache(f"jira:{key}")
        _log.info("Jira cache invalidated for %s", key)
    return {"status": "ok", "issue_key": key, "cache_invalidated_at": invalidated_at}


@router.post("/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: Optional[str] = Header(default=None),
) -> dict[str, Any]:
    """GitLab pipeline webhook — invalidates CI cache."""
    body = await request.body()
    settings = get_settings()
    secret = getattr(settings, "gitlab_webhook_secret", None) or ""
    if secret:
        if not x_gitlab_token:
            raise HTTPException(status_code=401, detail="Missing webhook token")
        if not hmac.compare_digest(secret, x_gitlab_token):
            raise HTTPException(status_code=401, detail="Invalid webhook token")
    payload: dict[str, Any] = {}
    if body:
        try:
            import json

            payload = json.loads(body.decode())
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    from app.services.kafka_producer import kafka_enabled, publish_webhook_event

    if kafka_enabled():
        publish_webhook_event("gitlab", "gitlab.pipeline", payload)
        project = (payload.get("project") or {}).get("path_with_namespace", "")
        return {"status": "accepted", "queued": True, "project": project}

    project = (payload.get("project") or {}).get("path_with_namespace", "")
    invalidated_at = None
    if project:
        invalidated_at = invalidate_ci_cache(f"gitlab:{project}")
    return {"status": "ok", "project": project, "cache_invalidated_at": invalidated_at}
