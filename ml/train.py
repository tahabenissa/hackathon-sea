"""Train the Isolation Forest baseline on NORMAL data only (Phase 5).

Output: models/isolation_forest.joblib (+ the feature list and training period).
"""


def main() -> None:
    # TODO Phase 5:
    #   - load data/processed/*.parquet, time-based split (train = earlier months)
    #   - X = build_features(train); fit StandardScaler + IsolationForest(random_state=42)
    #   - save pipeline + metadata (features, period, sklearn version) with joblib
    raise NotImplementedError


if __name__ == "__main__":
    main()
