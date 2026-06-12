"""TLS certificate expiry check for workspace domains."""

from __future__ import annotations

import socket
import ssl
from datetime import datetime, timezone
from typing import Any

from agents.schemas import ToolResult
from tools.context import ToolContext
from tools.sim_data import load_tools_fixture


def _check_domain_expiry(hostname: str) -> dict[str, Any] | None:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        if not cert:
            return None
        not_after = cert.get("notAfter")
        if not not_after:
            return None
        expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days = (expiry - datetime.now(timezone.utc)).days
        return {
            "domain": hostname,
            "cert_expiry_date": expiry.date().isoformat(),
            "days_remaining": days,
            "issuer": dict(x[0] for x in cert.get("issuer", ())) if cert.get("issuer") else {},
            "acm_managed": False,
            "renewal_status": "manual",
        }
    except Exception:
        return None


async def check_ssl_expiry(ctx: ToolContext) -> ToolResult:
    now = datetime.now(timezone.utc)
    prefs = ctx.extra.get("ui_preferences") if isinstance(ctx.extra.get("ui_preferences"), dict) else {}
    domains = prefs.get("tls_domains") or ctx.extra.get("tls_domains") or ["api.example.com"]
    if isinstance(domains, str):
        domains = [domains]

    raw: dict[str, Any] = {
        "cert_expiry_date": "",
        "days_remaining": 90,
        "affected_domains": [],
        "renewal_status": "ok",
        "acm_managed": False,
    }

    if ctx.sim_mode:
        data = load_tools_fixture(ctx.fixtures_dir, "devsecops_ssl_expiry")
        raw.update({k: data.get(k, raw[k]) for k in raw})
    else:
        worst_days = 999
        worst_domain = ""
        for host in domains[:5]:
            info = _check_domain_expiry(str(host))
            if info:
                raw["affected_domains"].append(info["domain"])
                if info["days_remaining"] < worst_days:
                    worst_days = info["days_remaining"]
                    worst_domain = info["domain"]
                    raw["cert_expiry_date"] = info["cert_expiry_date"]
                    raw["days_remaining"] = info["days_remaining"]
                    raw["renewal_status"] = info.get("renewal_status") or "manual"
        if worst_domain:
            raw["affected_domains"] = list(dict.fromkeys(raw["affected_domains"]))

    days = int(raw["days_remaining"])
    risk = 0.05
    if days <= 7:
        risk = 0.95
    elif days <= 30:
        risk = 0.65
    elif days <= 60:
        risk = 0.35

    lines = [
        f"TLS days remaining: {days}",
        f"Domains checked: {', '.join(raw['affected_domains'][:3]) or 'none'}",
    ]
    if days <= 7:
        lines.append("Certificate expiry imminent — release to affected services not recommended")

    return ToolResult(
        tool_name="check_ssl_expiry",
        signal=round(risk, 4),
        captured_at=now,
        raw_signals=raw,
        evidence_lines=lines,
    )
