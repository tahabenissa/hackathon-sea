"""Features for the AI anomaly layer, shared by training (ml/train.py) and the live engine.

ONE implementation, so offline and live features are identical.

Per buoy, from the sensors it really has (heterogeneous network):
  - current values           wave height, dominant period, wind speed, pressure
  - rates of change per hour vs the previous accepted reading (waves, wind, pressure)
Water temperature is left out: it changes slowly, is often missing (SS-B01: 49 %), and
is not what an attacker would fake to trigger or hide a storm warning.
"""

import math
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

VALUE_FIELDS = ("wave_height_m", "dominant_period_s", "wind_speed_ms", "pressure_hpa")
RATE_FIELDS = ("wave_height_m", "wind_speed_ms", "pressure_hpa")
MIN_GAP_H = 1.0  # buoys report hourly; a shorter gap still counts as one hour


def feature_names(sensors: Sequence[str]) -> list[str]:
    values = [f for f in VALUE_FIELDS if f in sensors]
    rates = [f"rate_{f}" for f in RATE_FIELDS if f in sensors]
    return values + rates


def feature_vector(names: Sequence[str], current: Mapping[str, float | None],
                   previous: Mapping[str, float | None] | None, gap_hours: float) -> list[float] | None:
    """Return the feature vector, or None if something needed is missing (= no opinion)."""
    hours = max(gap_hours, MIN_GAP_H)
    out: list[float] = []
    for name in names:
        if name.startswith("rate_"):
            field = name[5:]
            cur = current.get(field)
            prev = previous.get(field) if previous else None
            if cur is None or prev is None:
                return None
            out.append((cur - prev) / hours)
        else:
            v = current.get(name)
            if v is None or (isinstance(v, float) and math.isnan(v)):
                return None
            out.append(float(v))
    return out


def training_matrix(df: pd.DataFrame, sensors: Sequence[str]) -> pd.DataFrame:
    """Hourly cleaned data of one buoy -> feature rows (rows with missing inputs dropped)."""
    names = feature_names(sensors)
    frame = pd.DataFrame(index=df.index)
    gap_h = df.index.to_series().diff().dt.total_seconds().div(3600).clip(lower=MIN_GAP_H)
    for name in names:
        if name.startswith("rate_"):
            field = name[5:]
            frame[name] = df[field].diff() / gap_h
        else:
            frame[name] = df[name]
    return frame.replace([np.inf, -np.inf], np.nan).dropna()
