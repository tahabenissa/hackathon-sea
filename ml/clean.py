"""Parse + clean raw NOAA NDBC stdmet files into data/processed/<station>.parquet.

Usage:  python ml/clean.py <station> [<station> ...]

NDBC stdmet format (historical files):
  line 1: #YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS  TIDE
  line 2: units (skipped)
Missing values are encoded with a per-column sentinel (99, 999 or 9999). The sentinel
depends on the column: 999 is "missing" for WDIR/WTMP but a *valid* pressure in hPa,
so sentinels must be replaced column by column, never globally.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# NDBC column -> (SeaShield field, missing-value sentinel)
COLUMNS: dict[str, tuple[str, float]] = {
    "WVHT": ("wave_height_m", 99.0),
    "DPD": ("dominant_period_s", 99.0),
    "WSPD": ("wind_speed_ms", 99.0),
    "WDIR": ("wind_dir_deg", 999.0),
    "PRES": ("pressure_hpa", 9999.0),
    "WTMP": ("water_temp_c", 999.0),
}
FIELDS = [field for field, _ in COLUMNS.values()]

RESAMPLE = "1h"     # NDBC waves are reported hourly; met data often every 10 min
MAX_GAP_STEPS = 2   # interpolate gaps of at most 2 hours, leave longer gaps as NaN


def read_stdmet(path: Path) -> pd.DataFrame:
    """Read one raw NDBC stdmet file -> DataFrame with UTC index and SeaShield column names."""
    df = pd.read_csv(path, sep=r"\s+", skiprows=[1], dtype=str)
    df = df.rename(columns={"#YY": "YY"})
    time = pd.to_datetime(
        {
            "year": df["YY"].astype(int),
            "month": df["MM"].astype(int),
            "day": df["DD"].astype(int),
            "hour": df["hh"].astype(int),
            "minute": df["mm"].astype(int),
        },
        utc=True,
    )
    out = pd.DataFrame(index=pd.DatetimeIndex(time, name="time"))
    for ndbc_col, (field, sentinel) in COLUMNS.items():
        values = pd.to_numeric(df[ndbc_col], errors="coerce").to_numpy(dtype=float, copy=True)
        values[np.isclose(values, sentinel)] = np.nan
        out[field] = values
    return out


def resample_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """Hourly means; wind direction is averaged as a vector (350° and 10° -> 0°, not 180°)."""
    rad = np.deg2rad(df["wind_dir_deg"])
    tmp = df.drop(columns="wind_dir_deg").assign(_sin=np.sin(rad), _cos=np.cos(rad))
    hourly = tmp.resample(RESAMPLE).mean()
    hourly["wind_dir_deg"] = (np.rad2deg(np.arctan2(hourly["_sin"], hourly["_cos"])) + 360) % 360
    hourly = hourly.drop(columns=["_sin", "_cos"])[FIELDS]

    # Short gaps only, and never interpolate wind direction (circular quantity).
    for f in FIELDS:
        if f != "wind_dir_deg":
            hourly[f] = interpolate_short_gaps(hourly[f], MAX_GAP_STEPS)
    return hourly


def interpolate_short_gaps(s: pd.Series, max_gap: int) -> pd.Series:
    """Fill a gap only if the WHOLE gap is <= max_gap steps.

    pandas `interpolate(limit=n)` would also fill the first n steps of a long gap
    (e.g. a buoy that went offline in a hurricane), inventing data. This does not.
    """
    isna = s.isna()
    gap_len = isna.groupby((~isna).cumsum()).transform("sum")
    filled = s.interpolate(limit_area="inside")
    return filled.where(~isna | (gap_len <= max_gap))


def quality_report(station: str, df: pd.DataFrame) -> dict:
    wave = df["wave_height_m"]
    return {
        "station": station,
        "start": str(df.index.min()),
        "end": str(df.index.max()),
        "hours": len(df),
        "missing_pct": {c: round(float(df[c].isna().mean() * 100), 1) for c in FIELDS},
        "wave_height_max_m": None if wave.isna().all() else round(float(wave.max()), 2),
        "wave_height_max_time": None if wave.isna().all() else str(wave.idxmax()),
        "wave_height_p50_m": None if wave.isna().all() else round(float(wave.median()), 2),
        "wave_height_p99_m": None if wave.isna().all() else round(float(wave.quantile(0.99)), 2),
    }


def clean(station: str) -> dict:
    station = station.lower()
    files = sorted(RAW.glob(f"{station}h*.txt.gz"))
    if not files:
        raise FileNotFoundError(f"no raw files for {station} in {RAW} (run ml/download_ndbc.py)")
    raw = pd.concat([read_stdmet(f) for f in files]).sort_index()
    raw = raw[~raw.index.duplicated(keep="first")]
    hourly = resample_hourly(raw)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    hourly.to_parquet(PROCESSED / f"{station}.parquet")
    report = quality_report(station, hourly)
    report["source_files"] = [f.name for f in files]
    (PROCESSED / f"{station}_quality.json").write_text(json.dumps(report, indent=2))
    return report


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for station in sys.argv[1:]:
        print(json.dumps(clean(station), indent=2))


if __name__ == "__main__":
    main()
