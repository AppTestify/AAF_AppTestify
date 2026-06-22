"""Tenant-scoped LLM runtime invocation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.config import TenantAIProviderConfig, TenantSettings
from app.models.tenant import Tenant
from app.security import decrypt_json
from aaf.config import get_settings


class LLMInvocationError(Exception):
    pass


@dataclass
class ActiveProvider:
    provider_name: str
    model_name: str
    endpoint_url: Optional[str]
    temperature: Optional[float]
    max_tokens: Optional[int]
    timeout_seconds: int
    api_key: str
    metadata_json: dict[str, Any]


def _row_to_provider(row: TenantAIProviderConfig) -> Optional[ActiveProvider]:
    if not row.model_name:
        return None
    key_payload = decrypt_json(row.api_key_encrypted, secret=get_settings().app_encryption_key) if row.api_key_encrypted else {}
    api_key = str((key_payload or {}).get("api_key") or "")
    if not api_key and row.provider_name != "ollama":
        return None
    return ActiveProvider(
        provider_name=row.provider_name,
        model_name=row.model_name,
        endpoint_url=row.endpoint_url,
        temperature=row.temperature,
        max_tokens=row.max_tokens,
        timeout_seconds=max(2, int(row.timeout_seconds or 20)),
        api_key=api_key,
        metadata_json=row.metadata_json or {},
    )


def resolve_provider_chain(db: Session, tenant: Optional[Tenant]) -> list[ActiveProvider]:
    if tenant is None:
        return []
    settings_row = db.execute(select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)).scalar_one_or_none()
    if settings_row is None:
        return []
    rows = (
        db.execute(
            select(TenantAIProviderConfig).where(
                TenantAIProviderConfig.tenant_id == tenant.id,
                TenantAIProviderConfig.enabled.is_(True),
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return []
    converted = [p for p in (_row_to_provider(r) for r in rows) if p is not None]
    if not converted:
        return []
    default_name = settings_row.default_ai_provider
    if not default_name:
        return converted
    preferred = [p for p in converted if p.provider_name == default_name]
    rest = [p for p in converted if p.provider_name != default_name]
    return preferred + rest


def resolve_active_provider(db: Session, tenant: Optional[Tenant]) -> Optional[ActiveProvider]:
    chain = resolve_provider_chain(db, tenant)
    return chain[0] if chain else None


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def invoke_text(
    provider: ActiveProvider, prompt: str, system_prompt: Optional[str] = None
) -> tuple[str, dict[str, Any]]:
    started = time.time()
    usage: dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
    try:
        if provider.provider_name == "openai":
            text, usage = _invoke_openai(provider, prompt, system_prompt=system_prompt)
        elif provider.provider_name == "anthropic":
            text, usage = _invoke_anthropic(provider, prompt, system_prompt=system_prompt)
        elif provider.provider_name == "azure_openai":
            text, usage = _invoke_azure_openai(provider, prompt, system_prompt=system_prompt)
        elif provider.provider_name == "aws_bedrock":
            raise LLMInvocationError("aws_bedrock runtime invocation is not implemented")
        elif provider.provider_name == "ollama":
            text, usage = _invoke_ollama(provider, prompt, system_prompt=system_prompt)
        else:
            raise LLMInvocationError(f"unsupported provider: {provider.provider_name}")
    except Exception as exc:  # noqa: BLE001
        raise LLMInvocationError(str(exc)) from exc
    prompt_tokens = int(usage.get("prompt_tokens") or _estimate_tokens((system_prompt or "") + prompt))
    completion_tokens = int(usage.get("completion_tokens") or _estimate_tokens(text))
    return text, {
        "provider": provider.provider_name,
        "model": provider.model_name,
        "latency_ms": int((time.time() - started) * 1000),
        "status": "ok",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
    }


def invoke_json(
    provider: ActiveProvider, prompt: str, system_prompt: Optional[str] = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    text, meta = invoke_text(provider, prompt, system_prompt=system_prompt)
    try:
        return json.loads(_extract_json(text)), meta
    except Exception as exc:  # noqa: BLE001
        raise LLMInvocationError(f"invalid JSON response from provider: {exc}") from exc


def invoke_text_with_failover(
    providers: list[ActiveProvider], prompt: str, system_prompt: Optional[str] = None
) -> tuple[str, dict[str, Any]]:
    errors: list[dict[str, str]] = []
    for p in providers:
        try:
            return invoke_text(p, prompt, system_prompt=system_prompt)
        except Exception as exc:  # noqa: BLE001
            errors.append({"provider": p.provider_name, "model": p.model_name, "error": str(exc)})
    raise LLMInvocationError(f"all providers failed: {errors}")


def invoke_json_with_failover(
    providers: list[ActiveProvider], prompt: str, system_prompt: Optional[str] = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors: list[dict[str, str]] = []
    for p in providers:
        try:
            return invoke_json(p, prompt, system_prompt=system_prompt)
        except Exception as exc:  # noqa: BLE001
            errors.append({"provider": p.provider_name, "model": p.model_name, "error": str(exc)})
    raise LLMInvocationError(f"all providers failed: {errors}")


def _extract_json(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        parts = s.split("```")
        if len(parts) >= 3:
            s = parts[1]
            if s.startswith("json"):
                s = s[4:]
    return s.strip()


def _usage_from_body(body: dict[str, Any], provider_name: str) -> dict[str, int]:
    if provider_name == "anthropic":
        usage = body.get("usage") or {}
        return {
            "prompt_tokens": int(usage.get("input_tokens") or 0),
            "completion_tokens": int(usage.get("output_tokens") or 0),
        }
    usage = body.get("usage") or {}
    return {
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
    }


def _invoke_openai(
    provider: ActiveProvider, prompt: str, system_prompt: Optional[str] = None
) -> tuple[str, dict[str, int]]:
    url = provider.endpoint_url or "https://api.openai.com/v1/chat/completions"
    sys_content = system_prompt or "You are a governance reasoning assistant. Return concise, structured output."
    payload = {
        "model": provider.model_name,
        "messages": [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": prompt},
        ],
        "temperature": provider.temperature if provider.temperature is not None else 0.2,
    }
    if provider.max_tokens:
        payload["max_tokens"] = provider.max_tokens
    headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=provider.timeout_seconds) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()
    text = str((((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
    return text, _usage_from_body(body, "openai")


def _invoke_anthropic(
    provider: ActiveProvider, prompt: str, system_prompt: Optional[str] = None
) -> tuple[str, dict[str, int]]:
    url = provider.endpoint_url or "https://api.anthropic.com/v1/messages"
    payload = {
        "model": provider.model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": provider.max_tokens or 800,
    }
    if system_prompt:
        payload["system"] = system_prompt
    if provider.temperature is not None:
        payload["temperature"] = provider.temperature
    headers = {
        "x-api-key": provider.api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=provider.timeout_seconds) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()
    content = body.get("content") or []
    if content and isinstance(content, list):
        first = content[0] or {}
        text = str(first.get("text") or "").strip()
        return text, _usage_from_body(body, "anthropic")
    return "", {"prompt_tokens": 0, "completion_tokens": 0}


def _invoke_ollama(
    provider: ActiveProvider, prompt: str, system_prompt: Optional[str] = None
) -> tuple[str, dict[str, int]]:
    base = (provider.endpoint_url or "http://localhost:11434").rstrip("/")
    url = f"{base}/api/chat"
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": provider.model_name,
        "messages": messages,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if provider.api_key:
        headers["Authorization"] = f"Bearer {provider.api_key}"
    with httpx.Client(timeout=provider.timeout_seconds) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()
    text = str((body.get("message") or {}).get("content") or "").strip()
    return text, {"prompt_tokens": 0, "completion_tokens": 0}


def _invoke_azure_openai(
    provider: ActiveProvider, prompt: str, system_prompt: Optional[str] = None
) -> tuple[str, dict[str, int]]:
    if not provider.endpoint_url:
        raise LLMInvocationError("azure_openai requires endpoint_url")
    url = provider.endpoint_url
    if "api-version=" not in url:
        joiner = "&" if "?" in url else "?"
        url = f"{url}{joiner}api-version=2024-02-15-preview"
    sys_content = system_prompt or "You are a governance reasoning assistant. Return concise, structured output."
    payload = {
        "messages": [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": prompt},
        ],
        "temperature": provider.temperature if provider.temperature is not None else 0.2,
    }
    if provider.max_tokens:
        payload["max_tokens"] = provider.max_tokens
    headers = {"api-key": provider.api_key, "Content-Type": "application/json"}
    with httpx.Client(timeout=provider.timeout_seconds) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        body = resp.json()
    text = str((((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
    return text, _usage_from_body(body, "azure_openai")
