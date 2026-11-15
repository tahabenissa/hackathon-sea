"""Attack scenarios (see master prompt, section 6). Each one transforms messages.

Ground truth (which buoy/seq was attacked, with which scenario) is recorded by
the attacker in its own log / sent to the API, NEVER inside the message itself:
the engine must not be able to see the label.
"""

import copy
from datetime import UTC, datetime, timedelta
from typing import Any

from seashield.common import signing

Message = dict[str, Any]

# A hacked buoy sends an EXTRA reading between two real hourly ones.
FAKE_OBSERVATION_OFFSET = timedelta(minutes=30)


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _as_fresh_message(msg: Message, key: bytes) -> Message:
    """What a compromised buoy (T4) can do: craft a brand-new, validly signed message.

    New sequence number, nonce and send time, so the crypto gate sees nothing wrong.
    """
    forged = copy.deepcopy(msg)
    observed = datetime.fromisoformat(str(msg["observed_at"])) + FAKE_OBSERVATION_OFFSET
    forged.update(
        seq=int(msg["seq"]) + 1,
        ts=_iso(datetime.now(UTC)),
        observed_at=_iso(observed),
        nonce=signing.new_nonce(),
    )
    forged["sig"] = signing.sign(forged, key)
    return forged


def tamper_in_transit(msg: Message, field: str = "wave_height_m", value: float = 9.0) -> Message:
    """Scenario 1 (T1): man-in-the-middle edits a value WITHOUT the key -> signature breaks."""
    forged = copy.deepcopy(msg)
    forged["data"][field] = value
    return forged


def replay(captured: Message) -> Message:
    """Scenario 2 (T3): re-send an old valid message unchanged."""
    return copy.deepcopy(captured)


def compromised_spike(msg: Message, key: bytes, field: str = "wave_height_m",
                      value: float = 9.0) -> Message:
    """Scenario 3 (T4): attacker owns the buoy key and signs a fake value."""
    forged = copy.deepcopy(msg)
    forged["data"][field] = value
    return _as_fresh_message(forged, key)


def false_wind(msg: Message, key: bytes, wind_ms: float = 33.0) -> Message:
    """Scenario 4: signed storm-force wind while waves and pressure stay calm."""
    return compromised_spike(msg, key, field="wind_speed_ms", value=wind_ms)


def suppress(msg: Message, key: bytes, calm_wave_m: float = 1.0) -> Message:
    """Scenario 5: during a real storm, report calm sea (hide the danger)."""
    return compromised_spike(msg, key, field="wave_height_m", value=calm_wave_m)


def drift(msg: Message, key: bytes, step_index: int, step_m: float = 0.05) -> Message:
    """Scenario 6 (stretch, T5): slow additive drift on wave height."""
    forged = copy.deepcopy(msg)
    wave = forged["data"].get("wave_height_m")
    if wave is not None:
        forged["data"]["wave_height_m"] = round(wave + step_index * step_m, 2)
    return _as_fresh_message(forged, key)
