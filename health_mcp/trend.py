"""Trend calculation for get_trend (docs/基本設計.md §6: simple least-squares slope)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TrendResult:
    slope_per_day: float | None
    change_rate: float | None
    sample_count: int


def compute_trend(points: list[tuple[datetime, float]]) -> TrendResult:
    """Compute a linear-regression slope (value/day) and start->end change rate.

    points: list of (timestamp, value), any order, at least 1 point.
    Returns slope_per_day=None / change_rate=None when there aren't enough
    points to make either figure meaningful, rather than raising.
    """
    if not points:
        return TrendResult(slope_per_day=None, change_rate=None, sample_count=0)

    ordered = sorted(points, key=lambda p: p[0])
    n = len(ordered)
    t0 = ordered[0][0]
    xs = [(t - t0).total_seconds() / 86400.0 for t, _ in ordered]
    ys = [v for _, v in ordered]

    slope: float | None
    if n < 2:
        slope = None
    else:
        x_mean = sum(xs) / n
        y_mean = sum(ys) / n
        numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
        denominator = sum((x - x_mean) ** 2 for x in xs)
        slope = numerator / denominator if denominator else None

    first_value = ys[0]
    last_value = ys[-1]
    change_rate = (last_value - first_value) / first_value if first_value else None

    return TrendResult(slope_per_day=slope, change_rate=change_rate, sample_count=n)
