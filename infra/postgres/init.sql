-- Initial schema (Phase 7 may move this to Alembic migrations).

CREATE TABLE IF NOT EXISTS buoys (
    buoy_id       TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    ndbc_station  TEXT,
    lat           DOUBLE PRECISION,
    lon           DOUBLE PRECISION,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS measurements (
    id                  BIGSERIAL PRIMARY KEY,
    buoy_id             TEXT NOT NULL REFERENCES buoys(buoy_id),
    seq                 BIGINT NOT NULL,
    ts                  TIMESTAMPTZ NOT NULL,
    received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    data                JSONB NOT NULL,
    verdict             TEXT NOT NULL,      -- TRUSTED / REJECTED / SUSPECTED_FDI / ...
    risk                REAL,
    anomaly_score       REAL,
    is_simulated_attack BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_measurements_buoy_ts ON measurements (buoy_id, ts DESC);

CREATE TABLE IF NOT EXISTS incidents (
    id             BIGSERIAL PRIMARY KEY,
    measurement_id BIGINT REFERENCES measurements(id),
    buoy_id        TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    verdict        TEXT NOT NULL,
    evidence       JSONB NOT NULL,          -- list of per-layer evidence
    explanation    TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'OPEN',  -- OPEN / CONFIRMED_ATTACK / FALSE_POSITIVE
    reviewed_by    TEXT,
    reviewed_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS alerts (
    id          BIGSERIAL PRIMARY KEY,
    pipeline    TEXT NOT NULL,              -- 'unprotected' or 'seashield'
    buoy_id     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    kind        TEXT NOT NULL,              -- e.g. HIGH_WAVES
    state       TEXT NOT NULL,              -- ISSUED / HELD / RELEASED / DISCARDED
    incident_id BIGINT REFERENCES incidents(id)
);
