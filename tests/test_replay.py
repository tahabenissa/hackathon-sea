import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from seashield.common import signing
from seashield.common.registry import Buoy, load_buoys
from seashield.common.schema import Measurements, Verdict
from seashield.engine.baseline import naive_alert
from seashield.engine.pipeline import SecurityPipeline
from seashield.simulator.buoy import VirtualBuoy
from seashield.simulator.replay import replay

ROOT = Path(__file__).resolve().parents[1]
FULL = ("wave_height_m", "wind_speed_ms", "pressure_hpa")


@pytest.fixture
def tiny_network(tmp_path):
    t = pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC", name="time")
    pd.DataFrame({"wave_height_m": [1.0, 1.1, np.nan, 1.3], "wind_speed_ms": [5, 6, np.nan, 7],
                  "pressure_hpa": [1010, 1010, np.nan, 1009]}, index=t).to_parquet(tmp_path / "A.parquet")
    pd.DataFrame({"wave_height_m": [0.9, 1.0, 1.1, 1.2], "wind_speed_ms": [99, 99, 99, 99],
                  "pressure_hpa": [1, 1, 1, 1]}, index=t).to_parquet(tmp_path / "B.parquet")
    buoys = [Buoy("SS-A", "A", "A", 0, 0, FULL), Buoy("SS-B", "B", "B", 0, 1, ("wave_height_m",))]
    return buoys, tmp_path


def test_shared_clock_and_offline_hours(tiny_network):
    buoys, d = tiny_network
    ticks = list(replay(buoys, d))
    assert len(ticks) == 4
    assert set(ticks[0].readings) == {"SS-A", "SS-B"}
    assert set(ticks[2].readings) == {"SS-B"}           # SS-A offline that hour -> no message


def test_only_own_sensors_are_reported(tiny_network):
    buoys, d = tiny_network
    reading = next(iter(replay(buoys, d))).readings["SS-B"]
    assert reading.wave_height_m == 0.9
    assert reading.wind_speed_ms is None and reading.pressure_hpa is None


def test_start_end_window(tiny_network):
    buoys, d = tiny_network
    ticks = list(replay(buoys, d, start="2024-01-01T01:00", end="2024-01-01T02:00"))
    assert [t.observed_at.hour for t in ticks] == [1, 2]


def test_observed_at_is_signed(calm):
    key = b"k" * 32
    msg = VirtualBuoy("SS-B01", key).build_message(calm, observed_at=pd.Timestamp("2024-09-26", tz="UTC"))
    assert msg["observed_at"] == "2024-09-26T00:00:00Z"
    msg["observed_at"] = "2024-09-27T00:00:00Z"            # attacker shifts the measurement time
    assert not signing.verify(msg, key)


def test_restarted_buoy_continues_above_previous_seq(calm):
    first = VirtualBuoy("SS-B01", b"k" * 32)
    seqs = [first.build_message(calm)["seq"] for _ in range(50)]   # a burst, as in a real tick
    assert seqs == sorted(set(seqs))                               # strictly increasing
    time.sleep(0.02)                                               # a real restart takes far longer
    restarted = VirtualBuoy("SS-B01", b"k" * 32)
    assert restarted.next_seq > seqs[-1]
    assert seqs[-1] < 2**53                                        # exact in JavaScript


@pytest.mark.skipif(not (ROOT / "data/processed/42036.parquet").exists(),
                    reason="needs Phase 1 data (ml/clean.py)")
def test_real_hurricane_helene_end_to_end_without_broker():
    """Replay Helene from real NOAA data through signing + the full security pipeline."""
    buoys = load_buoys(ROOT / "config/buoys.yaml")
    keys = {b.buoy_id: bytes([i + 1]) * 32 for i, b in enumerate(buoys)}
    fleet = {b.buoy_id: VirtualBuoy(b.buoy_id, keys[b.buoy_id]) for b in buoys}
    pipeline = SecurityPipeline(keys, buoys)

    verdicts, baseline_alerts, max_wave = Counter(), 0, 0.0
    for tick in replay(buoys, ROOT / "data/processed", "2024-09-25T12:00", "2024-09-27T12:00"):
        for buoy_id, reading in tick.readings.items():
            raw = json.loads(json.dumps(fleet[buoy_id].build_message(reading, tick.observed_at)))
            verdicts[pipeline.process(raw).verdict] += 1
            baseline_alerts += naive_alert(raw) is not None
            max_wave = max(max_wave, reading.wave_height_m or 0.0)

    assert max_wave > 7                                   # the real storm is in the replay
    assert baseline_alerts > 0                            # the naive centre raises alerts
    assert verdicts[Verdict.REJECTED] == 0                # authentic data is never rejected
    assert verdicts[Verdict.SUSPECTED_FDI] == 0           # a real hurricane is not an "attack"


def test_measurements_from_none_values():
    assert Measurements(wave_height_m=None).wave_height_m is None
