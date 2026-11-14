from datetime import UTC, datetime, timedelta

from seashield.attacker import scenarios
from seashield.engine.crypto_gate import CryptoGate


def test_valid_message_passes(buoy, calm, keys):
    gate = CryptoGate(keys)
    assert gate.check(buoy.build_message(calm)).passed


def test_tampered_in_transit_rejected(buoy, calm, keys):
    gate = CryptoGate(keys)
    ev = gate.check(scenarios.tamper_in_transit(buoy.build_message(calm)))
    assert not ev.passed and "signature" in ev.detail


def test_unknown_device_rejected(calm, keys):
    from seashield.simulator.buoy import VirtualBuoy

    rogue = VirtualBuoy("SS-ROGUE", b"x" * 32)
    assert not CryptoGate(keys).check(rogue.build_message(calm)).passed


def test_replay_rejected(buoy, calm, keys):
    gate = CryptoGate(keys)
    msg = buoy.build_message(calm)
    assert gate.check(msg).passed
    ev = gate.check(scenarios.replay(msg))
    assert not ev.passed and "replay" in ev.detail


def test_stale_timestamp_rejected(buoy, calm, keys):
    later = datetime.now(UTC) + timedelta(minutes=10)
    gate = CryptoGate(keys, window_s=120, clock=lambda: later)
    ev = gate.check(buoy.build_message(calm))
    assert not ev.passed and "timestamp" in ev.detail


def test_compromised_buoy_passes_crypto(buoy, calm, keys):
    """T4: a stolen key makes a fake reading look authentic. Crypto alone cannot catch it."""
    gate = CryptoGate(keys)
    forged = scenarios.compromised_spike(buoy.build_message(calm), keys["SS-B01"])
    assert gate.check(forged).passed
