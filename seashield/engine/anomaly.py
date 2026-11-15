"""Layer 3: AI anomaly detection (Isolation Forest per buoy, trained on real 2023 data).

The score is EVIDENCE, never proof of an attack: real storms are unusual too. It is
calibrated on the 2023 training year (which contains Hurricane Idalia): 0.5 = as unusual
as the rarest 0.1 % of real 2023 readings, 1.0 = beyond anything seen in 2023.

Model file: models/isolation_forest.joblib, produced by ml/train.py. Without it the layer
gives no opinion (score None) and the rest of the engine works unchanged.
"""

import logging
from datetime import datetime
from pathlib import Path

import numpy as np

from seashield.common.schema import Evidence, Measurements
from seashield.engine.features import feature_vector

log = logging.getLogger("seashield.engine.anomaly")


def calibrated_score(s: float, q99: float, q999: float, smax: float) -> float:
    """0 below the training p99, 0.5 at the training p99.9 (alarm level), 1.0 at the max."""
    if s <= q99:
        return 0.0
    if s <= q999:
        return float(0.5 * (s - q99) / max(q999 - q99, 1e-9))
    return float(min(1.0, 0.5 + 0.5 * (s - q999) / max(smax - q999, 1e-9)))


class AnomalyDetector:
    def __init__(self, model_path: str | Path = "models/isolation_forest.joblib") -> None:
        self._models: dict = {}
        self._last: dict[str, tuple[datetime, dict]] = {}
        path = Path(model_path)
        if path.exists():
            import joblib  # local import: only needed when a model exists

            bundle = joblib.load(path)
            self._models = bundle["models"]
            log.info("AI anomaly models loaded for %s (trained on %s)",
                     ", ".join(self._models), bundle.get("trained_on"))
        else:
            log.warning("no AI model at %s: anomaly layer gives no opinion", path)

    @property
    def ready(self) -> bool:
        return bool(self._models)

    def reset(self) -> None:
        self._last.clear()

    def check(self, buoy_id: str, observed_at: datetime, m: Measurements) -> Evidence:
        spec = self._models.get(buoy_id)
        if spec is None:
            return Evidence(layer="anomaly", passed=True, score=None, detail="no AI model for this buoy")
        current = m.model_dump()
        prev = self._last.get(buoy_id)
        gap_h = (observed_at - prev[0]).total_seconds() / 3600 if prev else 1.0
        x = feature_vector(spec["features"], current, prev[1] if prev else None, gap_h)
        if x is None:
            return Evidence(layer="anomaly", passed=True, score=None,
                            detail="AI: not enough data for this reading")

        arr = np.asarray([x], dtype=float)
        s = float(-spec["model"].score_samples(arr)[0])
        score = calibrated_score(s, spec["q99"], spec["q999"], spec["smax"])
        z = spec["model"].named_steps["scale"].transform(arr)[0]
        top = sorted(zip(spec["features"], z, strict=True), key=lambda t: -abs(t[1]))[:2]
        why = ", ".join(f"{name} {zv:+.1f}σ" for name, zv in top)
        if score >= 0.5:
            detail = f"AI: rarer than 99.9 % of real 2023 readings (score {score:.2f}; {why})"
        elif score > 0:
            detail = f"AI: rare but seen before (score {score:.2f}; {why})"
        else:
            detail = "AI: typical sea behaviour"
        return Evidence(layer="anomaly", passed=score < 0.5, score=round(score, 3), detail=detail)

    def commit(self, buoy_id: str, observed_at: datetime, m: Measurements) -> None:
        """Called by the pipeline for ACCEPTED readings only (a fake must not become the reference)."""
        prev = self._last.get(buoy_id)
        if prev is None or observed_at > prev[0]:
            self._last[buoy_id] = (observed_at, m.model_dump())
