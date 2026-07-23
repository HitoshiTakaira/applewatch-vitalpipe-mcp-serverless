"""Shared-secret Bearer token verification for the Lambda Authorizer.

See docs/基本設計.md §3: comparison must be constant-time to avoid a timing
side-channel on the shared secret.
"""

from __future__ import annotations

import hmac

_BEARER_PREFIX = "Bearer "


def extract_bearer_token(headers: dict[str, str] | None) -> str | None:
    """Pull the token out of an `Authorization: Bearer <token>` header.

    API Gateway HTTP API lower-cases header names in the Lambda event, but we
    look up case-insensitively to not depend on that.
    """
    if not headers:
        return None
    for key, value in headers.items():
        if key.lower() == "authorization" and value.startswith(_BEARER_PREFIX):
            return value[len(_BEARER_PREFIX) :]
    return None


def is_valid_token(token: str | None, expected_secret: str) -> bool:
    """Constant-time comparison of the presented token against the shared secret."""
    if token is None:
        return False
    return hmac.compare_digest(token, expected_secret)
