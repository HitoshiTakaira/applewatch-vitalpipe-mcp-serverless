"""DynamoDB access layer for the single-table health data store.

Table schema (docs/基本設計.md §4):
  pk: "METRIC#{metric_name}" | "WORKOUT" | "SLEEP"
  sk: UTC ISO8601 timestamp, e.g. "2026-07-19T08:00:00Z"

Writes are idempotent by construction: pk/sk are derived deterministically
from the record's own timestamp, so re-ingesting the same HAE payload
overwrites the same item instead of creating a duplicate (要件定義.md F-8).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import boto3

# DynamoDB Query hard-caps a single page at 1MB; pulling pages of this many
# items keeps each request well under that regardless of item size, so
# get_metric_summary/get_trend can be tested with pagination without needing
# to construct a 1MB payload.
DEFAULT_PAGE_SIZE = 500

_table = None


def _table_name() -> str:
    return os.environ["DYNAMODB_TABLE_NAME"]


def get_table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(_table_name())
    return _table


def put_items(items: list[dict[str, Any]]) -> None:
    """Write records to the table, batching via DynamoDB's BatchWriteItem."""
    if not items:
        return
    table = get_table()
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)


def query_between(
    pk: str,
    start_sk: str,
    end_sk: str,
    *,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> Iterator[dict[str, Any]]:
    """Yield every item for `pk` with sk in [start_sk, end_sk], paginating as needed."""
    table = get_table()
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": ("pk = :pk AND sk BETWEEN :start_sk AND :end_sk"),
        "ExpressionAttributeValues": {
            ":pk": pk,
            ":start_sk": start_sk,
            ":end_sk": end_sk,
        },
        "Limit": page_size,
    }
    while True:
        response = table.query(**kwargs)
        yield from response.get("Items", [])
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return
        kwargs["ExclusiveStartKey"] = last_key
