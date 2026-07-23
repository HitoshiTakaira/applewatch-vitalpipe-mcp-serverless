"""Business logic behind the MCP tools (docs/基本設計.md §6).

Kept separate from the FastMCP tool wiring (handlers/mcp_function/app.py) so
it can be unit-tested by calling these functions directly, without going
through the ASGI/Lambda plumbing. Each function returns a plain dict,
including a `{"error": "..."}` shape for invalid input, rather than raising -
so a bad request from Claude Code always gets a clear message back instead of
a stack trace (基本設計.md §6).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from . import dynamo
from .timeutil import parse_query_date, to_sort_key
from .trend import compute_trend


def _as_float(value: Any) -> float:
    return float(value) if isinstance(value, Decimal) else value


def _validate_range(start_date: str, end_date: str) -> tuple[datetime, datetime] | dict[str, str]:
    try:
        start = parse_query_date(start_date)
        end = parse_query_date(end_date)
    except ValueError as exc:
        return {"error": str(exc)}
    if start > end:
        return {"error": f"start_date ({start_date}) is after end_date ({end_date})"}
    return start, end


def get_metric_summary(metric_name: str, start_date: str, end_date: str) -> dict[str, Any]:
    validated = _validate_range(start_date, end_date)
    if isinstance(validated, dict):
        return validated
    start, end = validated

    items = list(
        dynamo.query_between(f"METRIC#{metric_name}", to_sort_key(start), to_sort_key(end))
    )
    if not items:
        return {"metric_name": metric_name, "count": 0}

    values = [_as_float(item["value"]) for item in items]
    return {
        "metric_name": metric_name,
        "unit": items[0].get("unit"),
        "count": len(values),
        "average": sum(values) / len(values),
        "sum": sum(values),
        "max": max(values),
        "min": min(values),
    }


def get_workouts(start_date: str, end_date: str) -> dict[str, Any]:
    validated = _validate_range(start_date, end_date)
    if isinstance(validated, dict):
        return validated
    start, end = validated

    items = list(dynamo.query_between("WORKOUT", to_sort_key(start), to_sort_key(end)))
    workouts = [
        {
            "name": item.get("name"),
            "start": item.get("start"),
            "end": item.get("end"),
            "duration_minutes": _as_float(item.get("duration_minutes")),
            "energy_value": _as_float(item.get("energy_value")),
            "energy_unit": item.get("energy_unit"),
        }
        for item in items
    ]
    return {"count": len(workouts), "workouts": workouts}


def get_sleep_summary(start_date: str, end_date: str) -> dict[str, Any]:
    validated = _validate_range(start_date, end_date)
    if isinstance(validated, dict):
        return validated
    start, end = validated

    items = list(dynamo.query_between("SLEEP", to_sort_key(start), to_sort_key(end)))
    if not items:
        return {"nights": 0}

    fields = (
        "in_bed_hours",
        "asleep_hours",
        "awake_hours",
        "core_hours",
        "deep_hours",
        "rem_hours",
    )
    averages: dict[str, Any] = {}
    for field_name in fields:
        values = [_as_float(item[field_name]) for item in items if item.get(field_name) is not None]
        averages[f"avg_{field_name}"] = sum(values) / len(values) if values else None

    return {"nights": len(items), **averages}


def get_trend(metric_name: str, days: int) -> dict[str, Any]:
    if not isinstance(days, int) or days <= 0:
        return {"error": f"days must be a positive integer, got {days!r}"}

    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=days)
    items = list(
        dynamo.query_between(f"METRIC#{metric_name}", to_sort_key(start), to_sort_key(end))
    )
    if not items:
        return {"metric_name": metric_name, "days": days, "sample_count": 0}

    points = [
        (
            datetime.strptime(item["sk"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc),
            _as_float(item["value"]),
        )
        for item in items
    ]
    result = compute_trend(points)
    return {
        "metric_name": metric_name,
        "days": days,
        "unit": items[0].get("unit"),
        "sample_count": result.sample_count,
        "slope_per_day": result.slope_per_day,
        "change_rate": result.change_rate,
    }
