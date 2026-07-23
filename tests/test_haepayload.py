from decimal import Decimal

import pytest

from health_mcp.haepayload import parse_payload


def _base_payload():
    return {
        "data": {
            "metrics": [
                {
                    "name": "active_energy",
                    "units": "kJ",
                    "data": [
                        {
                            "date": "2026-07-19 08:00:00 +0900",
                            "qty": 721.3,
                            "source": "Apple Watch",
                        },
                    ],
                },
                {
                    # Units are declared per metric (not per entry, in this schema) — an
                    # unrecognized unit means every entry under it gets skipped.
                    "name": "basal_energy_burned",
                    "units": "cal",
                    "data": [
                        {
                            "date": "2026-07-19 09:00:00 +0900",
                            "qty": 100.0,
                            "source": "Apple Watch",
                        },
                    ],
                },
                {
                    "name": "step_count",
                    "units": "count",
                    "data": [
                        {"date": "2026-07-19 08:00:00 +0900", "qty": 1200, "source": "iPhone"},
                    ],
                },
                {
                    "name": "sleep_analysis",
                    "units": "hr",
                    "data": [
                        {
                            "date": "2026-07-19 07:00:00 +0900",
                            "sleepStart": "2026-07-18 23:00:00 +0900",
                            "sleepEnd": "2026-07-19 07:00:00 +0900",
                            "inBed": 8.0,
                            "asleep": 7.5,
                            "awake": 0.5,
                            "core": 4.0,
                            "deep": 1.5,
                            "rem": 2.0,
                            "source": "Apple Watch",
                        }
                    ],
                },
            ],
            "workouts": [
                {
                    "name": "Running",
                    "start": "2026-07-19 07:00:00 +0900",
                    "end": "2026-07-19 07:45:00 +0900",
                    "activeEnergy": {"qty": 350.0, "units": "kcal"},
                    "source": "Apple Watch",
                }
            ],
        }
    }


def test_parse_payload_missing_data_raises():
    with pytest.raises(ValueError):
        parse_payload({"unexpected": "shape"})


def test_parse_payload_converts_kj_to_kcal():
    result = parse_payload(_base_payload())

    energy_records = [r for r in result.records if r["pk"] == "METRIC#active_energy"]
    assert len(energy_records) == 1  # the "cal" entry is skipped
    record = energy_records[0]
    assert record["unit"] == "kcal"
    assert float(record["value"]) == pytest.approx(721.3 / 4.184, rel=1e-6)
    assert record["sk"] == "2026-07-18T23:00:00Z"


def test_parse_payload_skips_unknown_unit_with_reason():
    result = parse_payload(_base_payload())

    assert len(result.skipped) == 1
    assert "cal" in result.skipped[0]["reason"]


def test_parse_payload_passthrough_metric_keeps_unit():
    result = parse_payload(_base_payload())

    step_records = [r for r in result.records if r["pk"] == "METRIC#step_count"]
    assert len(step_records) == 1
    assert step_records[0]["unit"] == "count"
    assert step_records[0]["value"] == 1200.0


def test_parse_payload_sleep_entry():
    result = parse_payload(_base_payload())

    sleep_records = [r for r in result.records if r["pk"] == "SLEEP"]
    assert len(sleep_records) == 1
    record = sleep_records[0]
    assert record["sk"] == "2026-07-18T14:00:00Z"  # sleepStart, converted to UTC
    assert record["asleep_hours"] == Decimal("7.5")
    assert record["rem_hours"] == Decimal("2.0")


def test_parse_payload_workout_duration_and_energy():
    result = parse_payload(_base_payload())

    workouts = [r for r in result.records if r["pk"] == "WORKOUT"]
    assert len(workouts) == 1
    workout = workouts[0]
    assert workout["name"] == "Running"
    assert workout["duration_minutes"] == Decimal("45")
    assert workout["energy_value"] == Decimal("350.0")
    assert workout["energy_unit"] == "kcal"


def test_parse_payload_skips_malformed_entry_without_failing_others():
    payload = _base_payload()
    payload["data"]["metrics"][0]["data"].append({"qty": 1.0})  # missing "date"

    result = parse_payload(payload)

    # the malformed entry is skipped, the well-formed sibling entries still parse
    assert any("missing" in s["reason"] or "date" in s["reason"] for s in result.skipped)
    assert any(r["pk"] == "METRIC#active_energy" for r in result.records)
