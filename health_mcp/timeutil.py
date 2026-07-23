"""Timestamp parsing/formatting shared by ingest and query paths.

HAE emits local timestamps with a UTC offset (e.g. "2026-07-19 08:00:00 +0900").
We normalize everything to UTC before using it as a DynamoDB sort key: sk values
must be lexicographically sortable, which only holds if every item uses the same
offset. Converting to UTC at write time keeps BETWEEN queries correct regardless
of which timezone a given export was produced in (e.g. after DST changes).
"""

from __future__ import annotations

from datetime import datetime, timezone

HAE_DATE_FORMAT = "%Y-%m-%d %H:%M:%S %z"


def parse_hae_timestamp(raw: str) -> datetime:
    """Parse a HAE-style timestamp string into an aware datetime."""
    return datetime.strptime(raw.strip(), HAE_DATE_FORMAT)


def to_sort_key(dt: datetime) -> str:
    """Render an aware datetime as the UTC ISO8601 string used for DynamoDB sk."""
    if dt.tzinfo is None:
        raise ValueError("to_sort_key requires a timezone-aware datetime")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_query_date(raw: str) -> datetime:
    """Parse a user-supplied date/datetime (MCP tool argument) into UTC.

    Accepts plain dates ("2026-07-01") or full ISO8601 datetimes, with or
    without a UTC offset. Naive input is assumed to already be UTC, matching
    the sk format written by the ingest path.
    """
    text = raw.strip()
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid date: {raw!r} (expected ISO8601, e.g. 2026-07-01)") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
