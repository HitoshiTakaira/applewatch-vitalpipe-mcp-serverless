from datetime import datetime, timezone

import pytest

from health_mcp.timeutil import parse_hae_timestamp, parse_query_date, to_sort_key


def test_parse_hae_timestamp_keeps_offset():
    dt = parse_hae_timestamp("2026-07-19 08:00:00 +0900")
    assert (dt.year, dt.month, dt.day, dt.hour) == (2026, 7, 19, 8)
    assert dt.utcoffset().total_seconds() == 9 * 3600


def test_to_sort_key_normalizes_to_utc():
    dt = parse_hae_timestamp("2026-07-19 08:00:00 +0900")
    assert to_sort_key(dt) == "2026-07-18T23:00:00Z"


def test_to_sort_key_rejects_naive_datetime():
    with pytest.raises(ValueError):
        to_sort_key(datetime(2026, 7, 19))


def test_parse_query_date_naive_input_assumed_utc():
    dt = parse_query_date("2026-07-01")
    assert dt.tzinfo == timezone.utc


def test_parse_query_date_invalid_raises():
    with pytest.raises(ValueError):
        parse_query_date("not-a-date")
