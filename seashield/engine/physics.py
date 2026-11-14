"""Layer 2: physics-informed plausibility checks (cheap, explainable).

Time is measured with `observed_at` (when the sea was measured), never with the send
time `ts`, so fast replay of historical data does not distort rates (decision 0003).

Rate limits are PER HOUR. Phase 2 values come from the largest hourly changes measured on
3 years of real data (docs/data-notes.md §5), with a safety margin:
    wave height  max real 2.905 m/h  (SS-B03, Idalia)  -> limit 3.5 m/h
    wind speed   max real 11.8 m/s/h (SS-B04)          -> limit 15 m/s/h
    pressure     max real 15.35 hPa/h (SS-B01, Helene) -> limit 20 hPa/h
    water temp   max real 1.6 degC/h (SS-B03)          -> limit 3 degC/h
Final calibration (and false-positive check on train data) happens in Phase 5.1.
"""

from datetime import datetime, timedelta

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

# Max plausible change per hour of observation time
MAX_RATE_PER_HOUR: dict[str, float] = {
    "wave_height_m": 3.5,
    "wind_speed_ms": 15.0,
    "pressure_hpa": 20.0,
    "water_temp_c": 3.0,
}
# Buoys report on a fixed (hourly) schedule: a smaller gap still allows one hour of change.
MIN_RATE_WINDOW_H = 1.0

# Wind-sea consistency: big waves without wind need a long-period swell
BIG_WAVES_M = 5.0
CALM_WIND_MS = 5.0
SWELL_PERIOD_S = 11.0

# observed_at may not be later than the send time (+ clock skew)
MAX_CLOCK_SKEW = timedelta(seconds=120)


class PhysicsChecker:
    def __init__(self) -> None:
        self._last: dict[str, tuple[datetime, Measurements]] = {}

    def check(self, buoy_id: str, observed_at: datetime, m: Measurements,
              sent_at: datetime | None = None) -> Evidence:
        problems: list[str] = []
        values = m.model_dump()

        if sent_at is not None and observed_at > sent_at + MAX_CLOCK_SKEW:
            problems.append(f"measured at {observed_at} but sent earlier ({sent_at})")

        for name, (lo, hi) in RANGES.items():
            v = values.get(name)
            if v is not None and not lo <= v <= hi:
                problems.append(f"{name}={v} outside physical range [{lo}, {hi}]")

        prev = self._last.get(buoy_id)
        if prev is not None:
            prev_obs, prev_m = prev
            if observed_at <= prev_obs:
                problems.append(f"observation time {observed_at} not after previous {prev_obs}")
            else:
                hours = max((observed_at - prev_obs).total_seconds() / 3600.0, MIN_RATE_WINDOW_H)
                prev_values = prev_m.model_dump()
                for name, max_rate in MAX_RATE_PER_HOUR.items():
                    v, p = values.get(name), prev_values.get(name)
                    if v is not None and p is not None and abs(v - p) > max_rate * hours:
                        problems.append(
                            f"{name} jumped {p} -> {v} in {hours:.1f} h "
                            f"(max plausible {max_rate * hours:.1f})"
                        )

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

        # Only advance the per-buoy history with a time-consistent reading.
        if prev is None or observed_at > prev[0]:
            self._last[buoy_id] = (observed_at, m)

        if not problems:
            return Evidence(layer="physics", passed=True, score=0.0, detail="physically consistent")
        score = min(1.0, 0.5 + 0.25 * (len(problems) - 1))
        return Evidence(layer="physics", passed=False, score=score, detail="; ".join(problems))
