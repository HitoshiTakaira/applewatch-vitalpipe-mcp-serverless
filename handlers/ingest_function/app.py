"""IngestFunction: receives a HAE export payload and writes normalized records.

See docs/基本設計.md §2, §5, §9.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from health_mcp import dynamo
from health_mcp.haepayload import parse_payload

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _decode_body(event: dict[str, Any]) -> str:
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body).decode("utf-8")
    return body


def _response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload),
    }


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        raw_body = _decode_body(event)
        payload = json.loads(raw_body)
    except (ValueError, UnicodeDecodeError) as exc:
        logger.warning("rejecting request: invalid JSON body: %s", exc)
        return _response(400, {"error": f"invalid JSON body: {exc}"})

    try:
        result = parse_payload(payload)
    except ValueError as exc:
        logger.warning("rejecting request: %s", exc)
        return _response(400, {"error": str(exc)})

    dynamo.put_items(result.records)

    logger.info("ingested %d record(s), skipped %d", len(result.records), len(result.skipped))
    return _response(
        200,
        {
            "ingested": len(result.records),
            "skipped": len(result.skipped),
            "skipped_detail": result.skipped,
        },
    )
