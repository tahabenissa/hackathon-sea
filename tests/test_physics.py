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


def test_hourly_spike_flagged(calm):
    """The attack case: 1.5 m -> 9.0 m between two consecutive hourly observations."""
    checker = PhysicsChecker()
    checker.check("SS-B01", T0, calm)
    ev = checker.check("SS-B01", T0 + timedelta(hours=1), calm.model_copy(update={"wave_height_m": 9.0}))
    assert not ev.passed and "jumped" in ev.detail


def test_largest_real_hourly_change_is_allowed(calm):
    """Real max hourly wave change in 3 years of data was 2.905 m (data-notes §5)."""
    checker = PhysicsChecker()
    checker.check("SS-B01", T0, calm)
    real = calm.model_copy(update={"wave_height_m": 1.5 + 2.905})
    assert checker.check("SS-B01", T0 + timedelta(hours=1), real).passed


def test_rates_use_observation_time_not_send_time(calm):
    """Fast replay: two hourly observations sent 2 s apart must be judged over 1 hour."""
    checker = PhysicsChecker()
    sent = datetime(2026, 11, 14, 12, 0, 0, tzinfo=UTC)
    checker.check("SS-B01", T0, calm, sent_at=sent)
    storm_hour = calm.model_copy(update={"wave_height_m": 2.8})  # +1.3 m in one real hour
    ev = checker.check("SS-B01", T0 + timedelta(hours=1), storm_hour, sent_at=sent + timedelta(seconds=2))
    assert ev.passed


def test_longer_gap_allows_larger_change(calm):
    checker = PhysicsChecker()
    checker.check("SS-B01", T0, calm)
    after_outage = calm.model_copy(update={"wave_height_m": 7.0})  # +5.5 m after 6 h offline
    assert checker.check("SS-B01", T0 + timedelta(hours=6), after_outage).passed


def test_observation_time_going_backwards_flagged(calm):
    checker = PhysicsChecker()
    checker.check("SS-B01", T0, calm)
    ev = checker.check("SS-B01", T0 - timedelta(hours=1), calm)
    assert not ev.passed and "not after previous" in ev.detail


def test_observation_in_the_future_flagged(calm):
    ev = PhysicsChecker().check("SS-B01", T0 + timedelta(hours=1), calm, sent_at=T0)
    assert not ev.passed and "sent earlier" in ev.detail


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
