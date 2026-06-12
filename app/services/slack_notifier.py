"""Slack incoming webhook delivery with Block Kit-style messages."""

from __future__ import annotations

import logging
from typing import Any

import httpx

_log = logging.getLogger(__name__)


def build_blocks(*, title: str, body: str, fields: list[tuple[str, str]] | None = None, action_url: str | None = None) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": title[:150], "emoji": True}},
        {"type": "section", "text": {"type": "mrkdwn", "text": body[:3000]}},
    ]
    if fields:
        field_objs = [{"type": "mrkdwn", "text": f"*{k}*\n{v}"} for k, v in fields[:10]]
        blocks.append({"type": "section", "fields": field_objs})
    if action_url:
        blocks.append(
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Open"},
                        "url": action_url,
                    }
                ],
            }
        )
    return blocks


def send_slack_message(
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
    blocks = build_blocks(title=title, body=body, fields=fields, action_url=action_url)
    fallback = f"{title}\n{body}"
    if action_url:
        fallback = f"{fallback}\n{action_url}"
    payload = {"text": fallback[:4000], "blocks": blocks}
    try:
        resp = httpx.post(url, json=payload, timeout=10.0)
        if resp.status_code >= 400:
            _log.warning("slack_webhook_failed", extra={"status": resp.status_code})
    except Exception as exc:  # noqa: BLE001
        _log.warning("slack_webhook_error", extra={"error": str(exc)})
