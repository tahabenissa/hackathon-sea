# 0003: West Florida Shelf buoy cluster, observed_at field, time split

**Status:** accepted · 2026-11-14

**Context:** SeaShield needs real buoy data from neighbouring stations, including real extreme
events, to prove it detects attacks without flagging real storms. 11 eastern-Gulf NDBC
stations were surveyed for 2023–2025 (`ml/survey.py`).

**Decision**
1. Cluster: 42036 (SS-B01, full sensors), 42097 (SS-B02, waves), 42099 (SS-B03, waves),
   42013 (SS-B04, wind/pressure). Heterogeneous sensors are recorded in `config/buoys.yaml`.
2. Messages will carry a signed `observed_at` (measurement time) in addition to `ts` (send time).
   Physics rate checks use `observed_at`; replay protection uses `ts`.
3. Time split: train 2023, validation 2024-H1, test 2024-07 → 2025-12 (Debby, Helene, Milton).

**Consequences:** cross-buoy checks must handle missing sensors and offline neighbours
("no opinion", not "calm"). The physics rate limits must be recalibrated per hour (Phase 5.1).
Evidence for all of this: `docs/data-notes.md`.
