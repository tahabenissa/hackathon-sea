"""Phase 1 exploration of the chosen buoy cluster: statistics + figures.

Usage:  python ml/explore.py
Reads:  config/buoys.yaml, data/processed/<station>.parquet
Writes: docs/assets/phase1/*.png and docs/assets/phase1/stats.json

Every number in docs/data-notes.md comes from this script's output.
"""

import json
import sys
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from seashield.common.registry import load_buoys
from seashield.common.schema import Measurements
from seashield.engine.physics import PhysicsChecker
from seashield.engine.spatial import haversine_km

OUT = ROOT / "docs" / "assets" / "phase1"
FIELDS = ["wave_height_m", "dominant_period_s", "wind_speed_ms", "pressure_hpa", "water_temp_c"]

# Candidate event windows found in the data (Phase 1 survey). Names are the
# tropical cyclones whose dates match; verify against NHC reports when citing.
EVENTS = {
    "Idalia (2023-08-30)": ("2023-08-28", "2023-09-01"),
    "Winter front (2023-12-17)": ("2023-12-15", "2023-12-19"),
    "Debby (2024-08-04)": ("2024-08-02", "2024-08-06"),
    "Helene (2024-09-26)": ("2024-09-24", "2024-09-28"),
    "Milton (2024-10-09)": ("2024-10-07", "2024-10-11"),
}
NORMAL_WEEK = ("2024-05-06", "2024-05-13")

# Proposed time split (see docs/data-notes.md)
SPLIT = {
    "train": ("2023-01-01", "2023-12-31"),
    "validation": ("2024-01-01", "2024-06-30"),
    "test": ("2024-07-01", "2025-12-31"),
}


def load() -> tuple[list, dict[str, pd.DataFrame]]:
    buoys = load_buoys(ROOT / "config" / "buoys.yaml")
    data = {b.buoy_id: pd.read_parquet(ROOT / "data" / "processed" / f"{b.ndbc_station}.parquet")
            for b in buoys}
    return buoys, data


def hourly_change_stats(data: dict[str, pd.DataFrame]) -> dict:
    """Percentiles of |change| between consecutive hours: basis for physics rate limits."""
    stats = {}
    for bid, df in data.items():
        stats[bid] = {}
        for f in FIELDS:
            d = df[f].diff().abs().dropna()
            if len(d) == 0:
                continue
            stats[bid][f] = {q: round(float(d.quantile(p)), 3)
                             for q, p in [("p50", .5), ("p99", .99), ("p99.9", .999), ("max", 1.0)]}
    return stats


def neighbour_wave_stats(buoys, data) -> list[dict]:
    rows = []
    wave_buoys = [b for b in buoys if "wave_height_m" in b.sensors]
    for a, b in combinations(wave_buoys, 2):
        pair = pd.concat([data[a.buoy_id]["wave_height_m"], data[b.buoy_id]["wave_height_m"]],
                         axis=1, keys=["a", "b"]).dropna()
        diff = (pair["a"] - pair["b"]).abs()
        rows.append({
            "pair": f"{a.buoy_id}-{b.buoy_id}",
            "distance_km": round(haversine_km(a.lat, a.lon, b.lat, b.lon)),
            "overlap_hours": len(pair),
            "correlation": round(float(pair["a"].corr(pair["b"])), 3),
            "abs_diff_median_m": round(float(diff.median()), 2),
            "abs_diff_p95_m": round(float(diff.quantile(.95)), 2),
            "abs_diff_p99_m": round(float(diff.quantile(.99)), 2),
        })
    return rows


def event_table(data) -> list[dict]:
    rows = []
    for name, (a, b) in EVENTS.items():
        for bid, df in data.items():
            w = df.loc[a:b]
            rows.append({
                "event": name, "buoy": bid,
                "wave_max_m": _r(w["wave_height_m"].max()),
                "wind_max_ms": _r(w["wind_speed_ms"].max()),
                "pressure_min_hpa": _r(w["pressure_hpa"].min()),
                "wave_coverage_pct": round(float(w["wave_height_m"].notna().mean() * 100)),
            })
    return rows


def physics_on_real_data(data) -> dict:
    """How often do the CURRENT heuristic physics rules fire on real, unattacked data?"""
    result = {}
    for bid, df in data.items():
        checker, flagged, total, examples = PhysicsChecker(), 0, 0, []
        for ts, row in df.iterrows():
            values = {k: (None if pd.isna(v) else float(v)) for k, v in row.items()}
            if all(v is None for v in values.values()):
                continue
            ev = checker.check(bid, ts.to_pydatetime(), Measurements(**values))
            total += 1
            if not ev.passed:
                flagged += 1
                if len(examples) < 3:
                    examples.append(f"{ts}: {ev.detail}")
        result[bid] = {"hours_checked": total, "flagged": flagged,
                       "flagged_pct": round(100 * flagged / max(total, 1), 3), "examples": examples}
    return result


def split_summary(data) -> dict:
    out = {}
    for part, (a, b) in SPLIT.items():
        out[part] = {"from": a, "to": b,
                     "events": [n for n, (s, _) in EVENTS.items() if a <= s <= b],
                     "hours_with_waves_SS-B01": int(data["SS-B01"].loc[a:b, "wave_height_m"].notna().sum())}
    return out


def _r(x: float) -> float | None:
    return None if pd.isna(x) else round(float(x), 2)


# ----------------------------------------------------------------------------- figures

def plot_window(buoys, data, start, end, title, path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    for b in buoys:
        w = data[b.buoy_id].loc[start:end]
        label = f"{b.buoy_id} {b.name} ({b.ndbc_station})"
        if "wave_height_m" in b.sensors:
            axes[0].plot(w.index, w["wave_height_m"], label=label)
        if "wind_speed_ms" in b.sensors:
            axes[1].plot(w.index, w["wind_speed_ms"], label=label)
        if "pressure_hpa" in b.sensors:
            axes[2].plot(w.index, w["pressure_hpa"], label=label)
    for ax, ylab in zip(axes, ["Wave height (m)", "Wind speed (m/s)", "Pressure (hPa)"], strict=True):
        ax.set_ylabel(ylab)
        ax.grid(alpha=.3)
        ax.legend(fontsize=8, loc="upper left")
    axes[0].set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def plot_wave_vs_wind(data, path) -> None:
    df = data["SS-B01"].dropna(subset=["wave_height_m", "wind_speed_ms", "dominant_period_s"])
    fig, ax = plt.subplots(figsize=(8, 6))
    sc = ax.scatter(df["wind_speed_ms"], df["wave_height_m"], c=df["dominant_period_s"],
                    s=3, cmap="viridis", alpha=.5)
    fig.colorbar(sc, label="Dominant period (s)")
    ax.set_xlabel("Wind speed (m/s)")
    ax.set_ylabel("Wave height (m)")
    ax.set_title("SS-B01 West Tampa (42036), hourly, 2023-2025: waves vs wind")
    ax.grid(alpha=.3)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    buoys, data = load()

    stats = {
        "coverage_pct": {bid: {f: round(float(df[f].notna().mean() * 100), 1) for f in FIELDS}
                         for bid, df in data.items()},
        "hourly_change": hourly_change_stats(data),
        "neighbour_waves": neighbour_wave_stats(buoys, data),
        "events": event_table(data),
        "physics_heuristics_on_real_data": physics_on_real_data(data),
        "split": split_summary(data),
    }
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))

    plot_window(buoys, data, *NORMAL_WEEK, "Normal week (2024-05-06 to 05-13)", OUT / "normal_week.png")
    for name, (a, b) in EVENTS.items():
        if name.split()[0] in {"Idalia", "Helene", "Milton"}:
            plot_window(buoys, data, a, b, name, OUT / f"event_{name.split()[0].lower()}.png")
    plot_wave_vs_wind(data, OUT / "wave_vs_wind_42036.png")

    print(json.dumps(stats, indent=1, default=str))


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
