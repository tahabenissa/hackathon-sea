"""The UNPROTECTED monitoring centre, used as the comparison in the demo.

It trusts every message and fires an alert on a simple threshold. This is
deliberately naive: it shows what happens without SeaShield.
"""

from typing import Any

WAVE_ALERT_M = 6.0


def naive_alert(raw: dict[str, Any]) -> str | None:
    """Return an alert kind, or None. No authentication, no plausibility checks."""
    wave = (raw.get("data") or {}).get("wave_height_m")
    if wave is not None and wave > WAVE_ALERT_M:
        return "HIGH_WAVES"
    return None
