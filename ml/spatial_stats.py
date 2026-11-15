"""Measure how much REAL neighbouring buoys disagree, to set the Layer 4 tolerances.

Usage:  python ml/spatial_stats.py

For every pair of buoys and every sensor they BOTH have (heterogeneous network), compare
the hourly value of one buoy with the other buoy's value at the same hour and at +-1 h
(the engine accepts a neighbour reading up to 90 min away, and storms travel: Helene
peaked 4 h later at SS-B01 than at SS-B02).

Metrics (the ones seashield/engine/spatial.py uses):
  wave height  |ln((x + 1) / (y + 1))|   (disagreement grows with sea state: an absolute
                                          gap of 5 m is normal at 9 m seas, not at 1 m)
  wind speed   |x - y| in m/s            (the gap does not grow with wind speed)
  pressure     |x - y| in hPa            (reported only: see the Helene line)

Tolerance = the MAXIMUM on the training year 2023 (Idalia included), rounded up; then
checked on validation 2024-H1 and on Hurricane Helene (2024-09-24..28). Test data after
2024-07 (except the Helene window, already used as the demo storm) is not used to tune.
"""

import itertools
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from seashield.common.registry import load_buoys
from seashield.engine.spatial import haversine_km

FIELDS = ("wave_height_m", "wind_speed_ms", "pressure_hpa")
WAVE_OFFSET_M = 1.0
PERIODS = {
    "train 2023": ("2023-01-01", "2024-01-01"),
    "valid 2024-H1": ("2024-01-01", "2024-07-01"),
    "Helene": ("2024-09-24", "2024-09-29"),
}


def metric(field: str, x: pd.Series, y: pd.Series) -> pd.Series:
    if field == "wave_height_m":
        return np.abs(np.log((x + WAVE_OFFSET_M) / (y + WAVE_OFFSET_M)))
    return (x - y).abs()


def pair_values(a: pd.Series, b: pd.Series, field: str) -> pd.Series:
    parts = []
    for lag in (-1, 0, 1):
        j = pd.concat([a.rename("x"), b.shift(lag, freq="1h").rename("y")], axis=1, sort=True).dropna()
        parts.append(metric(field, j["x"], j["y"]))
    return pd.concat(parts)


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    buoys = load_buoys(ROOT / "config/buoys.yaml")
    data = {b.buoy_id: pd.read_parquet(ROOT / f"data/processed/{b.ndbc_station}.parquet") for b in buoys}
    pooled: dict[str, dict[str, list[pd.Series]]] = {f: {p: [] for p in PERIODS} for f in FIELDS}

    print("Per pair (value = metric; wave = |ln((x+1)/(y+1))|, wind m/s, pressure hPa)")
    for a, b in itertools.combinations(buoys, 2):
        shared = [f for f in FIELDS if f in a.sensors and f in b.sensors]
        km = haversine_km(a.lat, a.lon, b.lat, b.lon)
        for f in shared:
            v = pair_values(data[a.buoy_id][f], data[b.buoy_id][f], f)
            cells = []
            for name, (lo, hi) in PERIODS.items():
                s = v[(v.index >= lo) & (v.index < hi)]
                pooled[f][name].append(s)
                cells.append(f"{name}: n={len(s)} q99.9={s.quantile(.999):.2f} max={s.max():.2f}"
                             if len(s) else f"{name}: offline")
            print(f"  {a.buoy_id}-{b.buoy_id} ({km:.0f} km) {f}: " + " | ".join(cells))

    print("\nTolerance (train max, rounded up) and genuine readings beyond it:")
    for f, step in (("wave_height_m", 0.1), ("wind_speed_ms", 1.0), ("pressure_hpa", 1.0)):
        train = pd.concat(pooled[f]["train 2023"])
        tol = math.ceil(train.max() / step) * step
        line = [f"  {f}: train max {train.max():.3f} -> tolerance {tol:g}"]
        for name in ("valid 2024-H1", "Helene"):
            s = pd.concat(pooled[f][name])
            line.append(f"{name}: max {s.max():.2f}, {int((s > tol).sum())}/{len(s)} pairs beyond")
        print(" | ".join(line))

    print("\nAttack sizes in the same metric (wave):")
    for desc, x, y in (("spike 9.0 m vs neighbour 1.5 m", 9.0, 1.5),
                       ("spike +7.5 m on 1.5 m (9.0) vs 1.6 m", 9.0, 1.6),
                       ("suppress 1.0 m vs storm neighbour 6.0 m", 1.0, 6.0),
                       ("suppress 1.0 m vs Helene SS-B02 8.76 m", 1.0, 8.76)):
        print(f"  {desc}: {abs(math.log((x + WAVE_OFFSET_M) / (y + WAVE_OFFSET_M))):.2f}")


if __name__ == "__main__":
    main()
