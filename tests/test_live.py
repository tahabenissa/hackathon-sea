"""Attack console + live hub, without a broker: the hub's MQTT client is replaced by a fake."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from seashield.api.live import LiveHub
from seashield.common.schema import Measurements
from seashield.engine.baseline import naive_alert
from seashield.engine.events import build_event
from seashield.engine.pipeline import SecurityPipeline
from seashield.simulator.buoy import VirtualBuoy


class FakeClient:
    def __init__(self) -> None:
        self.published: list[dict] = []

    def publish(self, _topic, payload, qos=0):
        self.published.append(json.loads(payload))


@pytest.fixture
def setup(keys, calm):
    hub = LiveHub()
    hub._keys = keys
    hub._client = FakeClient()
    pipeline = SecurityPipeline(keys, buoys=[])
    buoy = VirtualBuoy("SS-B01", keys["SS-B01"])
    t0 = datetime(2024, 5, 6, tzinfo=UTC)

    def deliver(raw: dict) -> dict:
        """What the engine does, then what the hub receives back."""
        event = build_event(raw, pipeline.process(raw), naive_alert(raw))
        hub._on_event(event)
        return event

    for h in range(3):  # 3 real hourly readings: engine sees them, hub captures them
        raw = json.loads(json.dumps(buoy.build_message(calm, observed_at=t0 + timedelta(hours=h))))
        hub._capture(raw)
        deliver(raw)
    return hub, deliver


@pytest.mark.parametrize(("scenario", "verdict", "seashield", "unprotected"), [
    ("spike", "SUSPECTED_FDI", "HELD", "HIGH_WAVES"),      # fake alarm stopped
    ("suppress", "SUSPECTED_FDI", "REVIEW", None),        # calm 1 m after 1.5 m: small drop
    ("tamper", "REJECTED", "BLOCKED", "HIGH_WAVES"),       # forged 9 m never reaches alerts
    ("replay", "REJECTED", None, None),
])
def test_attack_is_labelled_and_detected(setup, scenario, verdict, seashield, unprotected):
    hub, deliver = setup
    hub.launch(scenario, "SS-B01")
    forged = hub._client.published[-1]
    event = deliver(forged)
    assert event["simulated_attack"] == scenario          # ground truth attached for display
    assert event["unprotected_alert"] == unprotected
    if scenario == "suppress":
        # 1.5 m -> 1.0 m in calm weather is physically plausible: honestly NOT detectable.
        # The suppression attack is only meaningful during a real storm (tested below).
        assert event["verdict"] == "TRUSTED"
        return
    assert event["verdict"] == verdict
    assert event["seashield_alert"] == seashield
    assert hub.stats_snapshot()["attacks_caught"] == 1


def test_suppression_during_storm_is_caught(keys):
    hub = LiveHub()
    hub._keys, hub._client = keys, FakeClient()
    pipeline = SecurityPipeline(keys, buoys=[])
    buoy = VirtualBuoy("SS-B01", keys["SS-B01"])
    storm = Measurements(wave_height_m=7.6, wind_speed_ms=28.0, dominant_period_s=12.0, pressure_hpa=954)
    t0 = datetime(2024, 9, 26, 22, tzinfo=UTC)
    for h in range(2):
        raw = json.loads(json.dumps(buoy.build_message(storm, observed_at=t0 + timedelta(hours=h))))
        hub._capture(raw)
        hub._on_event(build_event(raw, pipeline.process(raw), naive_alert(raw)))
    hub.launch("suppress", "SS-B01")
    forged = hub._client.published[-1]
    event = build_event(forged, pipeline.process(forged), naive_alert(forged))
    assert event["unprotected_alert"] is None        # unprotected centre: storm hidden
    assert event["verdict"] == "SUSPECTED_FDI"       # SeaShield: 7.6 m -> 1.0 m is implausible
    assert event["seashield_alert"] == "REVIEW"


def test_rate_limit(setup):
    hub, _ = setup
    hub.launch("spike", "SS-B01")
    with pytest.raises(RuntimeError):
        hub.launch("spike", "SS-B01")


def test_unknown_buoy_has_no_traffic(setup):
    hub, _ = setup
    with pytest.raises(LookupError):
        hub.launch("tamper", "SS-B03")
