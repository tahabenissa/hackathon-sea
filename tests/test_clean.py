import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))
from clean import interpolate_short_gaps, read_stdmet, resample_hourly

HEADER = (
    "#YY  MM DD hh mm WDIR WSPD GST  WVHT   DPD   APD MWD   PRES  ATMP  WTMP  DEWP  VIS  TIDE\n"
    "#yr  mo dy hr mn degT m/s  m/s     m   sec   sec degT   hPa  degC  degC  degC   mi    ft\n"
)


def _write(tmp_path: Path, rows: list[str]) -> Path:
    p = tmp_path / "test.txt"
    p.write_text(HEADER + "\n".join(rows) + "\n")
    return p


def test_sentinels_are_replaced_per_column(tmp_path):
    p = _write(tmp_path, [
        "2024 01 01 00 00 999 99.0 99.0 99.00 99.00 99.00 999 9999.0 999.0 999.0 999.0 99.0 99.00",
        # 999.0 hPa is a VALID (stormy) pressure and must be kept
        "2024 01 01 01 00  90  5.0  6.0  1.20  7.00  5.00 100  999.0  20.0  25.0  15.0 99.0 99.00",
    ])
    df = read_stdmet(p)
    assert df.iloc[0].isna().all()
    assert df.iloc[1]["pressure_hpa"] == 999.0
    assert df.iloc[1]["wave_height_m"] == 1.2
    assert str(df.index.tz) == "UTC"


def test_short_gap_filled_long_gap_untouched():
    s = pd.Series([1.0, np.nan, np.nan, 4.0, np.nan, np.nan, np.nan, np.nan, np.nan, 10.0])
    out = interpolate_short_gaps(s, max_gap=2)
    assert out.iloc[1:3].tolist() == [2.0, 3.0]          # gap of 2 -> filled
    assert out.iloc[4:9].isna().all()                     # gap of 5 -> NOT even partly filled


def test_no_extrapolation_after_last_value():
    s = pd.Series([1.0, 2.0, np.nan, np.nan])
    assert interpolate_short_gaps(s, max_gap=2).iloc[2:].isna().all()


def test_wind_direction_vector_mean():
    idx = pd.to_datetime(["2024-01-01 00:00", "2024-01-01 00:30"], utc=True)
    df = pd.DataFrame({"wave_height_m": [1, 1], "dominant_period_s": [5, 5], "wind_speed_ms": [5, 5],
                       "wind_dir_deg": [350.0, 10.0], "pressure_hpa": [1010, 1010],
                       "water_temp_c": [20, 20]}, index=idx)
    d = resample_hourly(df)["wind_dir_deg"].iloc[0]
    assert min(d, 360 - d) < 1e-6                        # ~0 deg, not 180 deg
