"""Auth email validator (localhost-friendly)."""

from __future__ import annotations

import pytest

from app.validators.email import parse_auth_email


def test_parse_accepts_localhost():
    assert parse_auth_email("Admin@localhost") == "admin@localhost"


def test_parse_accepts_normal_domain():
    assert parse_auth_email("User@Example.COM") == "user@example.com"


def test_parse_rejects_single_label_non_localhost():
    with pytest.raises(ValueError):
        parse_auth_email("a@intranet")


def test_parse_rejects_missing_at():
    with pytest.raises(ValueError):
        parse_auth_email("not-an-email")
