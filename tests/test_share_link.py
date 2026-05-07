"""Signed governance share tokens."""

from __future__ import annotations

import time

import pytest
from jose import jwt as jose_jwt

from aaf.config import get_settings
from app.services.share_link import decode_governance_share_token, mint_governance_share_token


def test_mint_and_decode_roundtrip(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-at-least-24-chars-long")
    token = mint_governance_share_token(run_id=42, tenant_id=7, ttl_seconds=3600)
    claims = decode_governance_share_token(token)
    assert claims["run_id"] == 42
    assert claims["tid"] == 7
    assert claims["typ"] == "gov_share"


def test_expired_token_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-at-least-24-chars-long")
    s = get_settings()
    now = int(time.time())
    token = jose_jwt.encode(
        {
            "run_id": 1,
            "tid": 1,
            "typ": "gov_share",
            "iat": now - 120,
            "exp": now - 60,
        },
        (s.share_link_signing_secret or s.jwt_secret).strip(),
        algorithm=s.jwt_algorithm,
    )
    with pytest.raises(ValueError, match="invalid or expired"):
        decode_governance_share_token(token)
