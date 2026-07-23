"""Unit normalization for HAE-reported energy values.

See docs/基本設計.md §5 for the source spec. kJ/kcal confusion in HAE's
Unit Preferences is the known bug this guards against (docs/要件定義.md §2).
"""

from __future__ import annotations

KJ_PER_KCAL = 4.184

# HAE unit string -> normalized (unit_name, converter) for energy-type metrics.
_ENERGY_CONVERSIONS = {
    "kJ": ("kcal", lambda value: value / KJ_PER_KCAL),
    "kcal": ("kcal", lambda value: value),
}


class UnknownUnitError(ValueError):
    """Raised when an energy value arrives in a unit we don't have a rule for."""

    def __init__(self, unit: str) -> None:
        self.unit = unit
        super().__init__(f"unknown energy unit: {unit!r}")


def normalize_energy(value: float, unit: str) -> tuple[float, str]:
    """Normalize an energy quantity to kcal.

    Returns (normalized_value, "kcal"). Raises UnknownUnitError for any unit
    that isn't explicitly handled, so callers can skip+log rather than
    silently persist a wrong value (docs/基本設計.md §5).
    """
    try:
        target_unit, convert = _ENERGY_CONVERSIONS[unit]
    except KeyError:
        raise UnknownUnitError(unit) from None
    return convert(value), target_unit
