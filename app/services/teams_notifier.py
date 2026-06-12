"""Microsoft Teams incoming webhook delivery (MessageCard / adaptive-style payload)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

_log = logging.getLogger(__name__)


def build_message_card(
    *,
    title: str,
    body: str,
    fields: list[tuple[str, str]] | None = None,
    action_url: str | None = None,
) -> dict[str, Any]:
    facts = [{"name": k, "value": v} for k, v in (fields or [])[:10]]
    card: dict[str, Any] = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "themeColor": "0078D4",
        "summary": title[:200],
        "title": title[:200],
        "text": body[:4000],
    }
    if facts:
        card["sections"] = [{"facts": facts}]
    if action_url:
        card["potentialAction"] = [
            {
                "@type": "OpenUri",
                "name": "Open",
                "targets": [{"os": "default", "uri": action_url}],
            }
        ]
    return card


def send_teams_message(
    webhook_url: str,
    *,
    title: str,
    body: str,
    fields: list[tuple[str, str]] | None = None,
    action_url: str | None = None,
) -> None:
    url = webhook_url.strip()
    if not url:
        return
    payload = build_message_card(title=title, body=body, fields=fields, action_url=action_url)
    try:
        resp = httpx.post(url, json=payload, timeout=10.0)
        if resp.status_code >= 400:
            _log.warning("teams_webhook_failed", extra={"status": resp.status_code})
    except Exception as exc:  # noqa: BLE001
        _log.warning("teams_webhook_error", extra={"error": str(exc)})
