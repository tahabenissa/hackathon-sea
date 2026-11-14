# ML pipeline

Run from the project root, in order:

| Step | Script | Output |
|---|---|---|
| 1. Download | `python ml/download_ndbc.py <station> <year> [<year> ...]` | `data/raw/<station>h<year>.txt.gz` |
| 2. Clean | `python ml/clean.py <station>` | `data/processed/<station>.parquet` |
| 3. Features | `ml/features.py` (imported by train/evaluate and the engine) | n/a |
| 4. Train | `python ml/train.py` | `models/isolation_forest.joblib` |
| 5. Evaluate | `python ml/evaluate.py` | `docs/evaluation.md` + plots |

Rules:
- **Time-based split** (train on earlier months, test on later months). Never shuffle.
- Train on normal data only. Inject labelled attacks into the test set only.
- Make sure the test period includes a **real storm** (it must NOT be flagged).
- Every number in `docs/evaluation.md` must come from a real run of `evaluate.py`.

Data: NOAA National Data Buoy Center, historical *standard meteorological* files.
Missing values are coded `99`, `999`, `9999` and must be converted to NaN.
