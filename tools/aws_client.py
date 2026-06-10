"""AWS boto3 client factory with graceful fallback."""

from __future__ import annotations

from typing import Any

from tools.context import ToolContext

_boto3: Any = None
_botocore: Any = None


def _load_boto3() -> tuple[Any, Any]:
    global _boto3, _botocore
    if _boto3 is None:
        import boto3 as b3
        import botocore as bc

        _boto3 = b3
        _botocore = bc
    return _boto3, _botocore


def get_aws_client(ctx: ToolContext, service: str) -> Any | None:
    if ctx.sim_mode:
        return None
    boto3, _ = _load_boto3()
    kwargs: dict[str, Any] = {"region_name": ctx.aws_region}
    if ctx.aws_access_key_id and ctx.aws_secret_access_key:
        kwargs["aws_access_key_id"] = ctx.aws_access_key_id
        kwargs["aws_secret_access_key"] = ctx.aws_secret_access_key
    try:
        return boto3.client(service, **kwargs)
    except Exception:
        return None
