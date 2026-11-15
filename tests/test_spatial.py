"""Layer 4: neighbour check (tolerances measured by ml/spatial_stats.py)."""

import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from seashield.attacker import scenarios
from seashield.common.registry import load_buoys
from seashield.common.schema import Measurements, Verdict
from seashield.engine.events import ESCALATED, build_event
from seashield.engine.pipeline import SecurityPipeline
from seashield.engine.spatial import SpatialChecker
from seashield.simulator.buoy import VirtualBuoy
from seashield.simulator.replay import replay

ROOT = Path(__file__).resolve().parents[1]
BUOYS = load_buoys(ROOT / "config/buoys.yaml")   # SS-B01 all, B02/B03 waves, B04 wind/pressure
KEYS = {b.buoy_id: bytes([i + 1]) * 32 for i, b in enumerate(BUOYS)}
T0 = datetime(2024, 9, 26, 22, tzinfo=UTC)


def waves(h: float) -> Measurements:
    return Measurements(wave_height_m=h, dominant_period_s=10.0)


def storm(h: float = 7.6) -> Measurements:
    return Measurements(wave_height_m=h, dominant_period_s=12.0, wind_speed_ms=25.0, pressure_hpa=960.0)


@pytest.fixture
def net():
    pipeline = SecurityPipeline(KEYS, BUOYS)
    fleet = {b.buoy_id: VirtualBuoy(b.buoy_id, KEYS[b.buoy_id]) for b in BUOYS}

    def send(buoy_id: str, m: Measurements, at: datetime = T0):
        raw = json.loads(json.dumps(fleet[buoy_id].build_message(m, observed_at=at)))
        return pipeline.process(raw), raw

    return pipeline, send


def spatial_of(result):
    return next(e for e in result.evidence if e.layer == "spatial")


def test_real_storm_agreed_by_neighbour_is_confirmed(net):
    _, send = net
    send("SS-B02", waves(7.0))
    result, _ = send("SS-B01", storm(7.6))
    assert result.verdict == Verdict.CONFIRMED_EVENT
    assert spatial_of(result).score == 0.0
    assert "SS-B02 (322 km)" in result.explanation


def test_lone_spike_disagreeing_with_fresh_neighbours_is_held(net):
    _, send = net
    send("SS-B02", waves(1.5))
    send("SS-B03", waves(1.6))
    result, _ = send("SS-B01", Measurements(wave_height_m=9.0, dominant_period_s=9.0, wind_speed_ms=12.0))
    ev = spatial_of(result)
    assert result.verdict == Verdict.SUSPECTED_FDI       # first reading: physics has no history
    assert not ev.passed and ev.score >= 0.5
    assert "SS-B03 (130 km) reports wave height 1.6 m; this buoy 9.0 m" in ev.detail


def test_one_agreeing_neighbour_is_enough(net):
    """Consensus: a storm front reaches neighbours at different times (Helene: 4 h lag)."""
    _, send = net
    send("SS-B02", waves(1.5))
    send("SS-B03", waves(5.5))
    result, _ = send("SS-B01", storm(6.5))
    assert spatial_of(result).passed
    assert result.verdict == Verdict.CONFIRMED_EVENT


def test_suppress_during_storm_is_escalated(net):
    _, send = net
    send("SS-B01", storm(7.6), T0 - timedelta(hours=1))
    send("SS-B02", waves(6.9))
    _, raw = send("SS-B01", storm(7.4))
    forged = scenarios.suppress(raw, KEYS["SS-B01"], calm_wave_m=1.0)
    pipeline, _ = net
    result = pipeline.process(forged)
    assert result.verdict == Verdict.SUPPRESSED_WARNING   # escalation wins over "implausible jump"
    assert "neighbour SS-B02 (322 km) reports wave height 6.9 m; this buoy 1.0 m" in result.explanation
    assert build_event(forged, result, None)["seashield_alert"] == ESCALATED


def test_stale_neighbour_gives_no_opinion(net):
    _, send = net
    send("SS-B02", waves(8.8), T0 - timedelta(hours=3))   # offline since: says nothing about now
    result, _ = send("SS-B01", Measurements(wave_height_m=1.0, wind_speed_ms=5.0))
    assert spatial_of(result).score is None
    assert result.verdict == Verdict.TRUSTED


def test_missing_neighbours_and_silent_sensor_give_no_opinion():
    sc = SpatialChecker(BUOYS)
    assert sc.check("SS-B01", T0, waves(9.0)).score is None              # nobody online
    sc.update("SS-B03", T0, Measurements(wave_height_m=None, water_temp_c=28.0))
    assert sc.check("SS-B01", T0, waves(9.0)).score is None              # wave sensor silent


def test_only_shared_sensors_are_compared():
    sc = SpatialChecker(BUOYS)
    sc.update("SS-B04", T0, Measurements(wind_speed_ms=6.0, pressure_hpa=1012.0))
    # SS-B02 has waves only, SS-B04 wind/pressure only: nothing to compare
    assert sc.check("SS-B02", T0, waves(9.0)).score is None
    # SS-B01 vs SS-B04: waves are not compared, wind is
    assert sc.check("SS-B01", T0, Measurements(wave_height_m=9.0, wind_speed_ms=8.0)).score == 0.0
    ev = sc.check("SS-B01", T0, Measurements(wave_height_m=1.0, wind_speed_ms=33.0))
    assert not ev.passed and "SS-B04 (214 km) reports wind 6.0 m/s; this buoy 33.0 m/s" in ev.detail
    # pressure is never compared (real Helene gap: 41 hPa)
    assert sc.check("SS-B01", T0, Measurements(wind_speed_ms=6.0, pressure_hpa=955.0)).passed


@pytest.mark.skipif(not (ROOT / "data/processed/42036.parquet").exists(),
                    reason="needs Phase 1 data (ml/clean.py)")
def test_real_helene_confirmed_and_suppression_at_peak_escalated():
    pipeline = SecurityPipeline(KEYS, BUOYS)
    fleet = {b.buoy_id: VirtualBuoy(b.buoy_id, KEYS[b.buoy_id]) for b in BUOYS}
    verdicts, last = Counter(), {}
    # up to SS-B01's real peak (7.58 m at 2024-09-26 22:00 UTC)
    for tick in replay(BUOYS, ROOT / "data/processed", "2024-09-25T12:00", "2024-09-26T22:00"):
        for buoy_id, reading in tick.readings.items():
            raw = json.loads(json.dumps(fleet[buoy_id].build_message(reading, tick.observed_at)))
            verdicts[pipeline.process(raw).verdict] += 1
            last[buoy_id] = raw
    peak = last["SS-B01"]
    assert peak["data"]["wave_height_m"] > 7
    assert verdicts[Verdict.SUSPECTED_FDI] == 0 and verdicts[Verdict.SUPPRESSED_WARNING] == 0
    assert verdicts[Verdict.CONFIRMED_EVENT] > 0          # real storm, agreed by SS-B02

    forged = scenarios.suppress(peak, KEYS["SS-B01"], calm_wave_m=1.0)
    assert pipeline.process(forged).verdict == Verdict.SUPPRESSED_WARNING
