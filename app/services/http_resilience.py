"""Shared HTTP resilience helpers for integration clients."""

from __future__ import annotations

import time
from typing import Any, Optional

import httpx


class IntegrationFetchError(Exception):
    """Raised when a remote integration call cannot be completed."""

    def __init__(self, message: str, *, category: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.category = category
        self.status_code = status_code


def classify_http_error(exc: Exception) -> tuple[str, Optional[int], str]:
    if isinstance(exc, httpx.TimeoutException):
        return "timeout", None, "request timed out"
    if isinstance(exc, httpx.ConnectError):
        return "network", None, "network connection failed"
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in {401, 403}:
            return "auth", status, "authentication/authorization failed"
        if status == 429:
            return "rate_limit", status, "rate limit exceeded"
        if status >= 500:
            return "upstream", status, "upstream server error"
        return "http", status, "http request failed"
    return "unknown", None, str(exc)


def get_json_with_retry(
    client: httpx.Client,
    url: str,
    *,
    attempts: int = 3,
    backoff_seconds: float = 0.35,
) -> dict[str, Any]:
    last_exc: Optional[Exception] = None
    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise IntegrationFetchError("non-dict json payload", category="schema")
            return payload
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < attempts:
                time.sleep(backoff_seconds * attempt)
                continue
            category, status, message = classify_http_error(exc)
            raise IntegrationFetchError(message, category=category, status_code=status) from exc
    raise IntegrationFetchError(str(last_exc or "unknown error"), category="unknown")
