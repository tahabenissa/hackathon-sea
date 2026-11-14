"""Replay real NOAA history as the buoy network's data ("digital twin").

All buoys share ONE historical clock, so a storm moves across the network exactly as it
did in reality (e.g. the 4 h lag between SS-B02 and SS-B01 in Helene).

A buoy only reports the fields it really has (`sensors` in config/buoys.yaml). An hour in
which all of its sensors are empty produces NO message, as when a real buoy goes offline.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from seashield.common.registry import Buoy
from seashield.common.schema import Measurements


@dataclass(frozen=True)
class Tick:
    """One step of the shared historical clock."""

    observed_at: datetime
    readings: dict[str, Measurements]  # buoy_id -> reading (offline buoys are absent)


def load_station(processed_dir: str | Path, buoy: Buoy) -> pd.DataFrame:
    """Cleaned hourly data of one buoy, restricted to its own sensors."""
    if buoy.ndbc_station is None:
        raise ValueError(f"{buoy.buoy_id} has no ndbc_station in config/buoys.yaml")
    df = pd.read_parquet(Path(processed_dir) / f"{buoy.ndbc_station}.parquet")
    sensors = [s for s in buoy.sensors if s in df.columns] or list(df.columns)
    return df[sensors]


def _to_measurements(row: pd.Series) -> Measurements | None:
    values = {k: float(v) for k, v in row.items() if pd.notna(v)}
    return Measurements(**values) if values else None


def replay(
    buoys: list[Buoy],
    processed_dir: str | Path = "data/processed",
    start: str | datetime | None = None,
    end: str | datetime | None = None,
) -> Iterator[Tick]:
    """Yield one Tick per historical hour in [start, end], for the whole network."""
    frames = {b.buoy_id: load_station(processed_dir, b) for b in buoys}
    clock = pd.DatetimeIndex(sorted(set().union(*(f.index for f in frames.values()))))
    if start is not None:
        clock = clock[clock >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        clock = clock[clock <= pd.Timestamp(end, tz="UTC")]

    for t in clock:
        readings = {}
        for buoy_id, df in frames.items():
            if t in df.index and (m := _to_measurements(df.loc[t])) is not None:
                readings[buoy_id] = m
        yield Tick(observed_at=t.to_pydatetime(), readings=readings)
