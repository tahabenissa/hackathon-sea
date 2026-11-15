"""Layer 4: cross-buoy (neighbour) verification.

A real storm shows up on nearby buoys too; a lie told by one hacked buoy does not.
Each reading is compared with the recent ACCEPTED readings of every other buoy that
  - measures the same sensor (the network is heterogeneous: SS-B02/B03 have waves only,
    SS-B04 wind/pressure only), and
  - is fresh: measured within FRESH_WINDOW of this reading (observation time, not wall clock).
A silent, offline or stale neighbour gives NO opinion, never "calm": storms knock buoys
offline (SS-B03 was offline for Helene and Milton, docs/data-notes.md section 2).

Tolerances are the largest disagreement between REAL neighbours in the training year
2023 (Hurricane Idalia included), rounded up, measured by `ml/spatial_stats.py`:
    wave height  |ln((x+1)/(y+1))|  train max 1.066 (SS-B01/SS-B03, Idalia)  -> 1.1
                 validation 2024-H1 max 0.82, Helene max 0.76: 0 genuine pairs beyond
    wind speed   |x - y|            train max 12.15 m/s (SS-B01/SS-B04)       -> 13 m/s
                 validation 2024-H1 max 12.93, Helene max 9.30: 0 genuine pairs beyond
    pressure     NOT compared: real gap reached 41.3 hPa in Helene (hurricane eye near
                 SS-B01), above the 2023 max of 26.7 hPa: it would flag the real storm.
Waves use a log ratio because real gaps grow with the sea state (5 m apart is normal in
9 m seas, impossible in 1 m seas). The tolerance does not depend on distance: the widest
real gap was on the CLOSEST pair (130 km, Idalia's core passed SS-B03).

Decisions returned to fusion:
  - disagreement: the reading is beyond tolerance of EVERY fresh neighbour on a sensor
    (consensus, so one lagging neighbour on a moving storm front cannot condemn it)
  - corroborated: the wave height agrees with at least one fresh neighbour
  - hidden storm: a fresh neighbour reports storm waves (>= the 6 m alert level) and this
    reading is far BELOW it (fail safe: ONE such neighbour is enough to escalate)
"""

import math
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta

from seashield.common.registry import Buoy
from seashield.common.schema import Evidence, Measurements
from seashield.engine.baseline import WAVE_ALERT_M

FRESH_WINDOW = timedelta(minutes=90)   # hourly network + 30 min offset of a forged reading
HISTORY = 4                            # readings kept per buoy (covers the window at 1/h)
WAVE_OFFSET_M = 1.0                    # keeps the log ratio sane near flat calm
WAVE_TOLERANCE = 1.1                   # |ln((x+1)/(y+1))|, ml/spatial_stats.py
WIND_TOLERANCE_MS = 13.0               # |x - y|, ml/spatial_stats.py
STORM_WAVES_M = WAVE_ALERT_M           # a neighbour "sees a storm" at the alert level
COMPARED = ("wave_height_m", "wind_speed_ms")
_LABEL = {"wave_height_m": ("wave height", "m"), "wind_speed_ms": ("wind", "m/s")}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def excess(field: str, x: float, y: float) -> float:
    """Disagreement divided by the real-data tolerance: > 1 means beyond anything real."""
    if field == "wave_height_m":
        return abs(math.log((x + WAVE_OFFSET_M) / (y + WAVE_OFFSET_M))) / WAVE_TOLERANCE
    return abs(x - y) / WIND_TOLERANCE_MS


@dataclass
class _Comparison:
    field: str
    neighbour: str
    km: float | None
    mine: float
    theirs: float
    excess: float

    def text(self) -> str:
        label, unit = _LABEL[self.field]
        where = f"{self.neighbour} ({self.km:.0f} km)" if self.km is not None else self.neighbour
        return f"neighbour {where} reports {label} {self.theirs:.1f} {unit}; this buoy {self.mine:.1f} {unit}"


@dataclass
class SpatialResult:
    evidence: Evidence
    corroborated: bool = False   # wave height agrees with at least one fresh neighbour
    hidden_storm: bool = False   # calm here while a fresh neighbour reports a storm


class SpatialChecker:
    def __init__(self, buoys: list[Buoy]) -> None:
        self._buoys = {b.buoy_id: b for b in buoys}
        self._recent: dict[str, deque[tuple[datetime, Measurements]]] = {}

    def update(self, buoy_id: str, ts: datetime, m: Measurements) -> None:
        """Store an ACCEPTED reading (only trusted data is a reference for the neighbours)."""
        self._recent.setdefault(buoy_id, deque(maxlen=HISTORY)).append((ts, m))

    def check(self, buoy_id: str, ts: datetime, m: Measurements) -> Evidence:
        return self.assess(buoy_id, ts, m).evidence

    def assess(self, buoy_id: str, ts: datetime, m: Measurements) -> SpatialResult:
        me = self._buoys.get(buoy_id)
        by_field: dict[str, list[_Comparison]] = {}
        for other_id, _, n_m in self._fresh(buoy_id, ts):
            other = self._buoys[other_id]
            for field in COMPARED:
                if not (_has(me, field) and _has(other, field)):
                    continue                              # heterogeneous network
                x, y = getattr(m, field), getattr(n_m, field)
                if x is None or y is None:
                    continue                              # sensor silent: no opinion
                by_field.setdefault(field, []).append(
                    _Comparison(field, other_id, _km(me, other), x, y, excess(field, x, y)))

        if not by_field:
            return SpatialResult(Evidence(
                layer="spatial", passed=True, score=None,
                detail="no fresh neighbour reading on a shared sensor (silent neighbours give no opinion)"))

        waves = by_field.get("wave_height_m", [])
        storm = [c for c in waves
                 if c.theirs >= STORM_WAVES_M and c.mine < STORM_WAVES_M and c.mine < c.theirs and c.excess > 1]
        if storm:
            worst = max(storm, key=lambda c: c.excess)
            return SpatialResult(
                Evidence(layer="spatial", passed=False, score=_score(worst.excess),
                         detail=f"{worst.text()}: far below a neighbour in a storm"),
                hidden_storm=True)

        disagreements = []
        for comps in by_field.values():
            if all(c.excess > 1 for c in comps):          # no fresh neighbour agrees
                disagreements.append(min(comps, key=lambda c: c.excess))
        corroborated = any(c.excess <= 1 for c in waves)
        if disagreements:
            worst = max(disagreements, key=lambda c: c.excess)
            detail = "; ".join(f"{c.text()}: beyond any real neighbour gap of 2023" for c in disagreements)
            return SpatialResult(Evidence(layer="spatial", passed=False, score=_score(worst.excess),
                                          detail=detail), corroborated=False)

        best = min((c for comps in by_field.values() for c in comps), key=lambda c: c.excess)
        agreeing = sum(c.excess <= 1 for comps in by_field.values() for c in comps)
        return SpatialResult(
            Evidence(layer="spatial", passed=True, score=0.0,
                     detail=f"consistent with {agreeing} fresh neighbour reading(s), e.g. {best.text()}"),
            corroborated=corroborated)

    def _fresh(self, buoy_id: str, ts: datetime):
        """Every accepted neighbour reading within FRESH_WINDOW; unknown or stale ones say nothing."""
        for other_id, readings in self._recent.items():
            if other_id == buoy_id or other_id not in self._buoys:
                continue
            for n_ts, n_m in readings:
                if abs(n_ts - ts) <= FRESH_WINDOW:
                    yield other_id, n_ts, n_m


def _has(buoy: Buoy | None, field: str) -> bool:
    """Buoys without a declared sensor list (tests, ad-hoc) are judged on the values sent."""
    return buoy is None or not buoy.sensors or field in buoy.sensors


def _km(a: Buoy | None, b: Buoy) -> float | None:
    if a is None or None in (a.lat, a.lon, b.lat, b.lon):
        return None
    return haversine_km(a.lat, a.lon, b.lat, b.lon)


def _score(ex: float) -> float:
    """Just beyond tolerance -> 0.5 (review); twice the largest real gap -> 1.0."""
    return round(min(1.0, 0.5 * ex), 3)
