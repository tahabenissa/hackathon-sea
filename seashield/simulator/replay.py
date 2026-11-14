"""Data source for virtual buoys: replay cleaned NOAA history (Phase 2).

Input: data/processed/<ndbc_station>.parquet produced by ml/clean.py, with
columns matching seashield.common.schema.Measurements.
"""

from collections.abc import Iterator
from pathlib import Path

from seashield.common.schema import Measurements


def replay_station(processed_file: str | Path, start: str | None = None) -> Iterator[Measurements]:
    """Yield one Measurements per historical time step, starting at `start` (ISO date)."""
    # TODO Phase 2:
    #   df = pd.read_parquet(processed_file); optionally df = df.loc[start:]
    #   for row in df.itertuples(): yield Measurements(**row_without_nans)
    raise NotImplementedError("Phase 2: replay cleaned NDBC data")
