"""Parse + clean raw NDBC stdmet files into data/processed/<station>.parquet (Phase 1).

NDBC stdmet columns: #YY MM DD hh mm WDIR WSPD GST WVHT DPD APD MWD PRES ATMP WTMP DEWP VIS TIDE
(line 1 = names, line 2 = units). Missing values: 99, 999, 9999.
"""

import sys

# Mapping NDBC column -> SeaShield Measurements field
COLUMNS = {
    "WVHT": "wave_height_m",
    "DPD": "dominant_period_s",
    "WSPD": "wind_speed_ms",
    "WDIR": "wind_dir_deg",
    "PRES": "pressure_hpa",
    "WTMP": "water_temp_c",
}
MISSING = [99.0, 999.0, 9999.0]


def clean(station: str) -> None:
    # TODO Phase 1:
    #   1. pd.read_csv(each data/raw/<station>h*.txt.gz, sep=r"\s+", skiprows=[1])
    #   2. build a UTC DatetimeIndex from #YY MM DD hh mm
    #   3. replace MISSING values per column with NaN, rename with COLUMNS
    #   4. resample to a fixed interval (e.g. 10 min or 1 h), short-gap interpolation only
    #   5. save data/processed/<station>.parquet and print a short data-quality report
    raise NotImplementedError


if __name__ == "__main__":
    clean(sys.argv[1])
