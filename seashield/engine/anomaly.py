"""Layer 3: ML anomaly detection (Phase 5).

Baseline: Isolation Forest trained by ml/train.py on NORMAL data only, saved to
models/isolation_forest.joblib. The score is evidence, never proof of an attack.
"""

from pathlib import Path

from seashield.common.schema import Evidence, Measurements


class AnomalyDetector:
    def __init__(self, model_path: str | Path = "models/isolation_forest.joblib") -> None:
        self._model_path = Path(model_path)
        self._model = None  # TODO Phase 5: joblib.load(self._model_path) if it exists

    @property
    def ready(self) -> bool:
        return self._model is not None

    def check(self, buoy_id: str, m: Measurements) -> Evidence:
        if not self.ready:
            return Evidence(layer="anomaly", passed=True, score=None, detail="model not trained yet")
        # TODO Phase 5:
        #   1. build the same feature vector as ml/features.py (values, deltas, rolling stats)
        #   2. raw = -self._model.score_samples([x])  -> map to 0..1
        #   3. return the top contributing features in `detail` for explainability
        raise NotImplementedError
