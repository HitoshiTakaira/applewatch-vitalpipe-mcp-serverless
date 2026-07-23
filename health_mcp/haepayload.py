"""Parse HAE export payloads into DynamoDB-ready records.

The payload shape implemented here follows docs/基本設計.md §9, which is
explicitly a PROVISIONAL schema pending confirmation against a real HAE
export (see docs/要件定義.md §2 and 基本設計.md §11). When real payloads are
available, expect to adjust field names here — this module is written so
that a single record's malformed/unexpected shape is skipped and logged
rather than failing the whole ingest (基本設計.md §9).

Expected shape:
    {
      "data": {
        "metrics": [
          {"name": "active_energy", "units": "kJ",
           "data": [{"date": "2026-07-19 08:00:00 +0900", "qty": 721.3, "source": "Apple Watch"}]},
          {"name": "sleep_analysis", "units": "hr",
           "data": [{"date": "...", "sleepStart": "...", "sleepEnd": "...",
                     "inBed": 8.0, "asleep": 7.5, "awake": 0.5,
                     "core": 4.0, "deep": 1.5, "rem": 2.0, "source": "Apple Watch"}]}
        ],
        "workouts": [
          {"name": "Running", "start": "...", "end": "...",
           "activeEnergy": {"qty": 350.0, "units": "kcal"}, "source": "Apple Watch"}
        ]
      }
    }
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .timeutil import parse_hae_timestamp, to_sort_key
from .units import UnknownUnitError, normalize_energy

logger = logging.getLogger(__name__)

# Metric names that represent an energy quantity and therefore go through
# kJ/kcal normalization. All other metrics are stored with whatever unit HAE
# reports, per 基本設計.md §5.
ENERGY_METRIC_NAMES = {"active_energy", "basal_energy_burned"}

SLEEP_METRIC_NAME = "sleep_analysis"
DEFAULT_SOURCE = "unknown"


@dataclass
class ParseResult:
    records: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)

    def _skip(self, kind: str, detail: dict[str, Any], reason: str) -> None:
        logger.warning("skipping %s record: %s (%s)", kind, detail, reason)
        self.skipped.append({"kind": kind, "detail": detail, "reason": reason})


def parse_payload(payload: dict[str, Any]) -> ParseResult:
    """Parse a decoded HAE JSON payload into normalized DynamoDB records.

    Raises ValueError if the payload doesn't even have the top-level
    `data` structure — that's a hard failure (ingest handler returns 400).
    Anything more granular (an unknown unit, a malformed single entry) is
    recorded in `ParseResult.skipped` instead of raising.
    """
    try:
        data = payload["data"]
    except (KeyError, TypeError) as exc:
        raise ValueError("payload is missing the top-level 'data' object") from exc

    result = ParseResult()
    for metric in data.get("metrics", []):
        _parse_metric(metric, result)
    for workout in data.get("workouts", []):
        _parse_workout(workout, result)
    return result


def _parse_metric(metric: dict[str, Any], result: ParseResult) -> None:
    name = metric.get("name")
    unit = metric.get("units")
    entries = metric.get("data", [])
    if not name or not isinstance(entries, list):
        result._skip("metric", metric, "missing name or data list")
        return

    if name == SLEEP_METRIC_NAME:
        for entry in entries:
            _parse_sleep_entry(entry, result)
        return

    is_energy = name in ENERGY_METRIC_NAMES
    for entry in entries:
        _parse_metric_entry(name, unit, entry, is_energy=is_energy, result=result)


def _parse_metric_entry(
    name: str,
    unit: str | None,
    entry: dict[str, Any],
    *,
    is_energy: bool,
    result: ParseResult,
) -> None:
    try:
        raw_value = float(entry["qty"])
        sk = to_sort_key(parse_hae_timestamp(entry["date"]))
    except Exception as exc:  # noqa: BLE001 - untrusted external payload, isolate to this entry
        result._skip("metric", entry, f"invalid entry for {name!r}: {exc}")
        return

    if is_energy:
        try:
            value, out_unit = normalize_energy(raw_value, unit or "")
        except UnknownUnitError as exc:
            result._skip("metric", entry, f"{name}: {exc}")
            return
    else:
        value, out_unit = raw_value, unit or ""

    result.records.append(
        {
            "pk": f"METRIC#{name}",
            "sk": sk,
            "value": Decimal(str(value)),
            "unit": out_unit,
            "source": entry.get("source", DEFAULT_SOURCE),
        }
    )


def _parse_sleep_entry(entry: dict[str, Any], result: ParseResult) -> None:
    try:
        anchor = entry.get("sleepStart") or entry["date"]
        sk = to_sort_key(parse_hae_timestamp(anchor))
        hours = {
            field_name: Decimal(str(float(entry[field_name])))
            for field_name in ("inBed", "asleep", "awake", "core", "deep", "rem")
            if field_name in entry
        }
    except Exception as exc:  # noqa: BLE001 - untrusted external payload, isolate to this entry
        result._skip("sleep", entry, f"invalid sleep entry: {exc}")
        return

    result.records.append(
        {
            "pk": "SLEEP",
            "sk": sk,
            "in_bed_hours": hours.get("inBed"),
            "asleep_hours": hours.get("asleep"),
            "awake_hours": hours.get("awake"),
            "core_hours": hours.get("core"),
            "deep_hours": hours.get("deep"),
            "rem_hours": hours.get("rem"),
            "source": entry.get("source", DEFAULT_SOURCE),
        }
    )


def _parse_workout(workout: dict[str, Any], result: ParseResult) -> None:
    try:
        name = workout["name"]
        start_dt = parse_hae_timestamp(workout["start"])
        end_dt = parse_hae_timestamp(workout["end"])
        energy = workout.get("activeEnergy") or {}
    except Exception as exc:  # noqa: BLE001 - untrusted external payload, isolate to this entry
        result._skip("workout", workout, f"invalid workout entry: {exc}")
        return

    try:
        energy_value, energy_unit = normalize_energy(float(energy["qty"]), energy.get("units", ""))
    except UnknownUnitError as exc:
        result._skip("workout", workout, f"{name}: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 - untrusted external payload, isolate to this entry
        result._skip("workout", workout, f"{name}: invalid energy value: {exc}")
        return

    duration_minutes = (end_dt - start_dt).total_seconds() / 60

    result.records.append(
        {
            "pk": "WORKOUT",
            "sk": to_sort_key(start_dt),
            "name": name,
            "start": to_sort_key(start_dt),
            "end": to_sort_key(end_dt),
            "duration_minutes": Decimal(str(duration_minutes)),
            "energy_value": Decimal(str(energy_value)),
            "energy_unit": energy_unit,
            "source": workout.get("source", DEFAULT_SOURCE),
        }
    )
