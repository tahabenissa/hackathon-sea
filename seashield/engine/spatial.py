"""Layer 4: cross-buoy verification (Phase 5).

Compare a reading with a distance-weighted estimate from neighbouring buoys.
Tolerance grows with distance. A real storm spreads across neighbours over
time; a lone spike on one buoy does not.
"""

import math
from datetime import datetime

from seashield.common.registry import Buoy
from seashield.common.schema import Evidence, Measurements


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class SpatialChecker:
    def __init__(self, buoys: list[Buoy]) -> None:
        self._buoys = {b.buoy_id: b for b in buoys}
        self._latest: dict[str, tuple[datetime, Measurements]] = {}

    def update(self, buoy_id: str, ts: datetime, m: Measurements) -> None:
        """Store the latest TRUSTED reading of each buoy (only trusted data is used as reference)."""
        self._latest[buoy_id] = (ts, m)

    def check(self, buoy_id: str, ts: datetime, m: Measurements) -> Evidence:
        # TODO Phase 5:
        #   - neighbours = other buoys with a recent trusted reading and known lat/lon
        #   - expected = inverse-distance-weighted mean of their values
        #   - residual / tolerance(distance) -> score 0..1
        #   - also return whether neighbours show a storm (needed for SUPPRESSED_WARNING)
        return Evidence(layer="spatial", passed=True, score=None, detail="not implemented yet")
