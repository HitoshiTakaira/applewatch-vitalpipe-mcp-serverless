from datetime import datetime, timedelta, timezone

import pytest

from health_mcp.trend import compute_trend


def test_compute_trend_increasing_series():
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    points = [(base + timedelta(days=i), 10.0 + i) for i in range(5)]

    result = compute_trend(points)

    assert result.slope_per_day == pytest.approx(1.0)
    assert result.change_rate == pytest.approx((14.0 - 10.0) / 10.0)
    assert result.sample_count == 5


def test_compute_trend_flat_series_has_zero_slope():
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    points = [(base + timedelta(days=i), 42.0) for i in range(3)]

    result = compute_trend(points)

    assert result.slope_per_day == pytest.approx(0.0)
    assert result.change_rate == pytest.approx(0.0)


def test_compute_trend_single_point_has_no_slope():
    result = compute_trend([(datetime.now(timezone.utc), 5.0)])

    assert result.slope_per_day is None
    assert result.change_rate == pytest.approx(0.0)
    assert result.sample_count == 1


def test_compute_trend_empty():
    result = compute_trend([])

    assert result.slope_per_day is None
    assert result.change_rate is None
    assert result.sample_count == 0


def test_compute_trend_unordered_input_is_sorted_first():
    base = datetime(2026, 7, 1, tzinfo=timezone.utc)
    points = [
        (base + timedelta(days=2), 30.0),
        (base, 10.0),
        (base + timedelta(days=1), 20.0),
    ]

    result = compute_trend(points)

    assert result.slope_per_day == pytest.approx(10.0)
