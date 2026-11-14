"""Compare candidate NDBC stations to choose the SeaShield buoy cluster (Phase 1).

Usage:  python ml/survey.py <station> [<station> ...]
Needs:  raw files from ml/download_ndbc.py and data/raw/meta/station_table.txt
Prints: completeness of each SeaShield field, wave statistics, and pairwise distances.
"""

import re
import sys
from itertools import combinations
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean import FIELDS, PROCESSED, clean

from seashield.engine.spatial import haversine_km

STATION_TABLE = Path(__file__).resolve().parents[1] / "data" / "raw" / "meta" / "station_table.txt"
LOC = re.compile(r"([\d.]+) ([NS]) ([\d.]+) ([EW])")


def station_meta() -> dict[str, dict]:
    meta = {}
    for line in STATION_TABLE.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("#"):
            continue
        parts = line.split("|")
        if len(parts) < 7 or not (m := LOC.search(parts[6])):
            continue
        lat = float(m[1]) * (1 if m[2] == "N" else -1)
        lon = float(m[3]) * (1 if m[4] == "E" else -1)
        meta[parts[0].lower()] = {"name": parts[4].strip(), "type": parts[2].strip(), "lat": lat, "lon": lon}
    return meta


def main() -> None:
    stations = [s.lower() for s in sys.argv[1:]]
    meta = station_meta()
    rows = []
    for s in stations:
        try:
            r = clean(s)
        except FileNotFoundError:
            print(f"{s}: no data downloaded, skipped")
            continue
        miss = r["missing_pct"]
        rows.append({
            "station": s,
            "name": meta.get(s, {}).get("name", "?")[:38],
            "hours": r["hours"],
            **{f"miss_{k.split('_')[0]}": v for k, v in miss.items()},
            "wave_p50": r["wave_height_p50_m"],
            "wave_p99": r["wave_height_p99_m"],
            "wave_max": r["wave_height_max_m"],
            "wave_max_time": (r["wave_height_max_time"] or "")[:16],
        })
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print("\nMissing % per field (after hourly resampling):")
    print(pd.DataFrame(rows).to_string(index=False))

    print("\nPairwise distances (km):")
    ok = [s for s in stations if s in meta and (PROCESSED / f"{s}.parquet").exists()]
    for a, b in combinations(ok, 2):
        d = haversine_km(meta[a]["lat"], meta[a]["lon"], meta[b]["lat"], meta[b]["lon"])
        print(f"  {a}-{b}: {d:6.0f}")
    print("\nFields:", ", ".join(FIELDS))


if __name__ == "__main__":
    main()
