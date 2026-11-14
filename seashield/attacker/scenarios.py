"""Attack scenarios (see master prompt, section 6). Each one transforms messages.

Ground truth (which buoy/seq was attacked, with which scenario) is recorded by
the attacker in its own log / sent to the API, NEVER inside the message itself:
the engine must not be able to see the label.
"""

import copy
from typing import Any

from seashield.common import signing

Message = dict[str, Any]


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
    """Scenario 3 (T4): attacker owns the buoy key and re-signs a fake value."""
    forged = copy.deepcopy(msg)
    forged["data"][field] = value
    forged["sig"] = signing.sign(forged, key)
    return forged


def false_wind(msg: Message, key: bytes, wind_ms: float = 33.0) -> Message:
    """Scenario 4: signed storm-force wind while waves and pressure stay calm."""
    return compromised_spike(msg, key, field="wind_speed_ms", value=wind_ms)


def suppress(msg: Message, key: bytes, calm_wave_m: float = 1.6) -> Message:
    """Scenario 5: during a real storm, report calm sea (hide the danger)."""
    return compromised_spike(msg, key, field="wave_height_m", value=calm_wave_m)


def drift(msg: Message, key: bytes, step_index: int, step_m: float = 0.05) -> Message:
    """Scenario 6 (stretch, T5): slow additive drift on wave height."""
    forged = copy.deepcopy(msg)
    wave = forged["data"].get("wave_height_m")
    if wave is not None:
        forged["data"]["wave_height_m"] = round(wave + step_index * step_m, 2)
    forged["sig"] = signing.sign(forged, key)
    return forged
