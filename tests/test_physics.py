from datetime import UTC, datetime, timedelta

from seashield.common.schema import Measurements
from seashield.engine.physics import PhysicsChecker

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_calm_sea_is_consistent(calm):
    assert PhysicsChecker().check("SS-B01", T0, calm).passed


def test_impossible_value_flagged():
    ev = PhysicsChecker().check("SS-B01", T0, Measurements(wave_height_m=-3))
    assert not ev.passed and "outside physical range" in ev.detail


def test_sudden_jump_flagged(calm):
    checker = PhysicsChecker()
    checker.check("SS-B01", T0, calm)
    spike = calm.model_copy(update={"wave_height_m": 9.0})
    ev = checker.check("SS-B01", T0 + timedelta(minutes=10), spike)
    assert not ev.passed and "jumped" in ev.detail


def test_big_waves_without_wind_flagged():
    m = Measurements(wave_height_m=9.0, wind_speed_ms=2.0, dominant_period_s=7.0)
    ev = PhysicsChecker().check("SS-B01", T0, m)
    assert not ev.passed and "wind" in ev.detail


def test_storm_with_matching_wind_is_consistent():
    storm = Measurements(wave_height_m=8.0, wind_speed_ms=22.0, dominant_period_s=10.0,
                         pressure_hpa=985.0)
    assert PhysicsChecker().check("SS-B01", T0, storm).passed


def test_long_swell_without_local_wind_is_consistent():
    swell = Measurements(wave_height_m=5.5, wind_speed_ms=3.0, dominant_period_s=15.0)
    assert PhysicsChecker().check("SS-B01", T0, swell).passed
