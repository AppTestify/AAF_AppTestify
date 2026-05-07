"""JWT-signed, time-limited public URLs for governance run snapshots."""

from __future__ import annotations

import time
from typing import Any

from jose import JWTError, jwt

from aaf.config import get_settings

_SHARE_TYP = "gov_share"


def _signing_secret() -> str:
    s = get_settings()
    raw = (s.share_link_signing_secret or s.jwt_secret).strip()
    if not raw:
        raise ValueError("share link signing secret is not configured")
    return raw


def mint_governance_share_token(*, run_id: int, tenant_id: int, ttl_seconds: int) -> str:
    if ttl_seconds < 60:
        raise ValueError("ttl_seconds must be at least 60")
    now = int(time.time())
    claims: dict[str, Any] = {
        "run_id": run_id,
        "tid": tenant_id,
        "typ": _SHARE_TYP,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    s = get_settings()
    return jwt.encode(claims, _signing_secret(), algorithm=s.jwt_algorithm)


def decode_governance_share_token(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        claims = jwt.decode(
            token,
            _signing_secret(),
            algorithms=[s.jwt_algorithm],
            options={"require": ["exp", "iat"]},
        )
    except JWTError as exc:
        raise ValueError("invalid or expired share token") from exc
    if claims.get("typ") != _SHARE_TYP:
        raise ValueError("invalid share token type")
    run_id = claims.get("run_id")
    tid = claims.get("tid")
    if not isinstance(run_id, int) or not isinstance(tid, int):
        raise ValueError("invalid share token payload")
    return claims
