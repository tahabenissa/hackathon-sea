"""Train the AI anomaly layer: one Isolation Forest per buoy, on REAL 2023 data only.

Usage:  python ml/train.py
Output: models/isolation_forest.joblib  (+ printed training summary)

The training year contains real extreme weather (Hurricane Idalia, Dec 2023 front): the
model must learn that storms are part of normal ocean behaviour. No attack data is used.

Score calibration (per buoy), with s = -score_samples(x) (higher = more unusual):
  q99  = 99th percentile of s on the training data
  q999 = 99.9th percentile (the alarm level: ~0.1 % of real 2023 readings are above it)
  smax = max of s on the training data
  anomaly score = 0 below q99, 0.5 at q999, 1.0 at smax and beyond.
  (First version used smax as the alarm level: too strict, the AI caught almost nothing on
  validation, see docs/PHASE_D6.md.)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from seashield.common.registry import load_buoys
from seashield.engine.features import training_matrix

ROOT = Path(__file__).resolve().parents[1]
TRAIN = ("2023-01-01", "2023-12-31")
OUT = ROOT / "models" / "isolation_forest.joblib"


def main() -> None:
    models, summary = {}, {}
    for b in load_buoys(ROOT / "config" / "buoys.yaml"):
        df = pd.read_parquet(ROOT / "data" / "processed" / f"{b.ndbc_station}.parquet")
        X = training_matrix(df.loc[TRAIN[0]:TRAIN[1]], b.sensors)
        model = Pipeline([
            ("scale", StandardScaler()),
            ("iforest", IsolationForest(n_estimators=200, random_state=42)),
        ]).fit(X.to_numpy())
        s = -model.score_samples(X.to_numpy())
        models[b.buoy_id] = {
            "model": model,
            "features": list(X.columns),
            "q99": float(pd.Series(s).quantile(0.99)),
            "q999": float(pd.Series(s).quantile(0.999)),
            "smax": float(s.max()),
            "train_rows": len(X),
        }
        summary[b.buoy_id] = {"features": list(X.columns), "train_rows": len(X),
                              "q99": round(models[b.buoy_id]["q99"], 4),
                              "q999": round(models[b.buoy_id]["q999"], 4),
                              "smax": round(models[b.buoy_id]["smax"], 4)}

    OUT.parent.mkdir(exist_ok=True)
    joblib.dump({
        "models": models,
        "trained_on": TRAIN,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sklearn": sklearn.__version__,
    }, OUT)
    print(json.dumps(summary, indent=2))
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
