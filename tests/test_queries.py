from datetime import datetime, timedelta, timezone
from decimal import Decimal

from health_mcp import dynamo, queries
from health_mcp.timeutil import to_sort_key


def test_get_metric_summary_aggregates(dynamodb_table):
    dynamo.put_items(
        [
            {
                "pk": "METRIC#active_energy",
                "sk": "2026-07-01T00:00:00Z",
                "value": Decimal("100"),
                "unit": "kcal",
            },
            {
                "pk": "METRIC#active_energy",
                "sk": "2026-07-02T00:00:00Z",
                "value": Decimal("200"),
                "unit": "kcal",
            },
            {
                "pk": "METRIC#active_energy",
                "sk": "2026-07-03T00:00:00Z",
                "value": Decimal("300"),
                "unit": "kcal",
            },
        ]
    )

    result = queries.get_metric_summary("active_energy", "2026-07-01", "2026-07-03")

    assert result["count"] == 3
    assert result["average"] == 200
    assert result["sum"] == 600
    assert result["max"] == 300
    assert result["min"] == 100
    assert result["unit"] == "kcal"


def test_get_metric_summary_no_data(dynamodb_table):
    result = queries.get_metric_summary("active_energy", "2026-01-01", "2026-01-02")

    assert result == {"metric_name": "active_energy", "count": 0}


def test_get_metric_summary_invalid_range_returns_error(dynamodb_table):
    result = queries.get_metric_summary("active_energy", "2026-07-05", "2026-07-01")

    assert "error" in result


def test_get_metric_summary_invalid_date_returns_error(dynamodb_table):
    result = queries.get_metric_summary("active_energy", "not-a-date", "2026-07-01")

    assert "error" in result


def test_get_workouts_returns_list(dynamodb_table):
    dynamo.put_items(
        [
            {
                "pk": "WORKOUT",
                "sk": "2026-07-19T00:00:00Z",
                "name": "Running",
                "start": "2026-07-19T00:00:00Z",
                "end": "2026-07-19T00:45:00Z",
                "duration_minutes": Decimal("45"),
                "energy_value": Decimal("350"),
                "energy_unit": "kcal",
            }
        ]
    )

    result = queries.get_workouts("2026-07-01", "2026-07-31")

    assert result["count"] == 1
    assert result["workouts"][0]["name"] == "Running"
    assert result["workouts"][0]["duration_minutes"] == 45.0


def test_get_sleep_summary_averages(dynamodb_table):
    dynamo.put_items(
        [
            {
                "pk": "SLEEP",
                "sk": "2026-07-18T14:00:00Z",
                "in_bed_hours": Decimal("8"),
                "asleep_hours": Decimal("7"),
                "awake_hours": Decimal("1"),
                "core_hours": Decimal("4"),
                "deep_hours": Decimal("1"),
                "rem_hours": Decimal("2"),
            },
            {
                "pk": "SLEEP",
                "sk": "2026-07-19T14:00:00Z",
                "in_bed_hours": Decimal("6"),
                "asleep_hours": Decimal("5"),
                "awake_hours": Decimal("1"),
                "core_hours": Decimal("3"),
                "deep_hours": Decimal("1"),
                "rem_hours": Decimal("1"),
            },
        ]
    )

    result = queries.get_sleep_summary("2026-07-01", "2026-07-31")

    assert result["nights"] == 2
    assert result["avg_asleep_hours"] == 6.0
    assert result["avg_in_bed_hours"] == 7.0


def test_get_sleep_summary_no_data(dynamodb_table):
    assert queries.get_sleep_summary("2026-01-01", "2026-01-02") == {"nights": 0}


def test_get_trend_positive_slope(dynamodb_table):
    now = datetime.now(tz=timezone.utc)
    dynamo.put_items(
        [
            {
                "pk": "METRIC#active_energy",
                "sk": to_sort_key(now - timedelta(days=offset)),
                "value": Decimal(str(100 - offset * 10)),
                "unit": "kcal",
            }
            for offset in range(4, -1, -1)  # oldest (4 days ago) to newest (today)
        ]
    )

    result = queries.get_trend("active_energy", days=7)

    assert result["sample_count"] == 5
    assert result["slope_per_day"] > 0
    assert result["unit"] == "kcal"


def test_get_trend_invalid_days_returns_error(dynamodb_table):
    result = queries.get_trend("active_energy", days=0)

    assert "error" in result
