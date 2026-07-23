import pytest

from health_mcp.units import UnknownUnitError, normalize_energy


def test_kcal_passes_through_unchanged():
    value, unit = normalize_energy(100.0, "kcal")
    assert value == 100.0
    assert unit == "kcal"


def test_kj_converts_to_kcal():
    value, unit = normalize_energy(4.184, "kJ")
    assert value == pytest.approx(1.0)
    assert unit == "kcal"


def test_unknown_unit_raises():
    with pytest.raises(UnknownUnitError):
        normalize_energy(100.0, "cal")
