# ML pipeline

Run from the project root, in order (install with `pip install -e ".[dev,ml]"`):

| Step | Script | Output | Status |
|---|---|---|---|
| 1. Download | `python ml/download_ndbc.py <station> <year> [<year> ...]` | `data/raw/<station>h<year>.txt.gz` | ✅ |
| 1b. Survey candidates | `python ml/survey.py <station> [...]` | comparison table (stdout) | ✅ |
| 2. Clean | `python ml/clean.py <station> [...]` | `data/processed/<station>.parquet` + `_quality.json` | ✅ |
| 2b. Explore | `python ml/explore.py` | `docs/assets/phase1/` (stats.json + figures) | ✅ |
| 3. Features | `ml/features.py` (imported by train/evaluate and the engine) | n/a | Phase 5 |
| 4. Train | `python ml/train.py` | `models/isolation_forest.joblib` | Phase 5 |
| 5. Evaluate | `python ml/evaluate.py` | `docs/evaluation.md` + plots | Phase 6 |

Chosen cluster (Phase 1): **42036, 42097, 42099, 42013**. See `config/buoys.yaml` and
[`docs/data-notes.md`](../docs/data-notes.md).

Rules:
- **Time-based split**: train 2023, validation 2024-H1, test 2024-07 → 2025-12. Never shuffle.
- Train on real, unattacked data (natural storms included). Inject labelled attacks only into
  copies of validation/test data.
- The test period contains real hurricanes (Debby, Helene, Milton). They must NOT be flagged.
- Every number in `docs/` must come from a real run of these scripts.

Data: NOAA National Data Buoy Center, historical *standard meteorological* files.
Missing values use per-column sentinels (`99`, `999`, `9999`), handled in `clean.py`.
