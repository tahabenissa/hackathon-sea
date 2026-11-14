"""Layer 2: physics-informed plausibility checks (cheap, explainable).

All thresholds below are INITIAL HEURISTICS. Calibrate them on the NOAA NDBC
data in Phase 5 and record the final values in docs/decisions/.
"""

from datetime import datetime

from seashield.common.schema import Evidence, Measurements

# Physically possible ranges (anything outside is impossible, not just rare)
RANGES: dict[str, tuple[float, float]] = {
    "wave_height_m": (0.0, 30.0),
    "dominant_period_s": (1.0, 30.0),
    "wind_speed_ms": (0.0, 85.0),
    "wind_dir_deg": (0.0, 360.0),
    "pressure_hpa": (870.0, 1090.0),
    "water_temp_c": (-2.5, 40.0),
}

# Max plausible change per minute between two consecutive readings
MAX_RATE_PER_MIN: dict[str, float] = {
    "wave_height_m": 0.3,
    "wind_speed_ms": 3.0,
    "pressure_hpa": 0.5,
    "water_temp_c": 0.2,
}

# Wind-sea consistency: big waves without wind need a long-period swell
BIG_WAVES_M = 5.0
CALM_WIND_MS = 5.0
SWELL_PERIOD_S = 11.0


class PhysicsChecker:
    def __init__(self) -> None:
        self._last: dict[str, tuple[datetime, Measurements]] = {}

    def check(self, buoy_id: str, ts: datetime, m: Measurements) -> Evidence:
        problems: list[str] = []
        values = m.model_dump()

        for name, (lo, hi) in RANGES.items():
            v = values.get(name)
            if v is not None and not lo <= v <= hi:
                problems.append(f"{name}={v} outside physical range [{lo}, {hi}]")

        prev = self._last.get(buoy_id)
        if prev is not None:
            prev_ts, prev_m = prev
            minutes = max((ts - prev_ts).total_seconds() / 60.0, 1.0)
            prev_values = prev_m.model_dump()
            for name, max_rate in MAX_RATE_PER_MIN.items():
                v, p = values.get(name), prev_values.get(name)
                if v is not None and p is not None and abs(v - p) / minutes > max_rate:
                    problems.append(f"{name} jumped {p} -> {v} in {minutes:.0f} min")

        if (
            m.wave_height_m is not None
            and m.wind_speed_ms is not None
            and m.wave_height_m >= BIG_WAVES_M
            and m.wind_speed_ms < CALM_WIND_MS
            and (m.dominant_period_s is None or m.dominant_period_s < SWELL_PERIOD_S)
        ):
            problems.append(
                f"{m.wave_height_m} m waves with only {m.wind_speed_ms} m/s wind and no long swell"
            )

        self._last[buoy_id] = (ts, m)

        if not problems:
            return Evidence(layer="physics", passed=True, score=0.0, detail="physically consistent")
        score = min(1.0, 0.5 + 0.25 * (len(problems) - 1))
        return Evidence(layer="physics", passed=False, score=score, detail="; ".join(problems))
