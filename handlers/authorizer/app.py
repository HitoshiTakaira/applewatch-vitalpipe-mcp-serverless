"""Lambda Authorizer (REQUEST type, HTTP API simple response format).

Validates `Authorization: Bearer <secret>` against the shared secret held in
SSM Parameter Store. See docs/基本設計.md §3.
"""

from __future__ import annotations

import os
from typing import Any

import boto3

from health_mcp.auth import extract_bearer_token, is_valid_token

_ssm = None
_secret_cache: str | None = None


def _get_secret() -> str:
    global _ssm, _secret_cache
    if _secret_cache is None:
        if _ssm is None:
            _ssm = boto3.client("ssm")
        parameter_name = os.environ["SECRET_PARAMETER_NAME"]
        response = _ssm.get_parameter(Name=parameter_name, WithDecryption=True)
        _secret_cache = response["Parameter"]["Value"]
    return _secret_cache


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    token = extract_bearer_token(event.get("headers"))
    authorized = is_valid_token(token, _get_secret())
    return {"isAuthorized": authorized}
