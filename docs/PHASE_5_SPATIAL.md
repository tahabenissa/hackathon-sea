# Phase 5: Layer 4, the neighbour (cross-buoy) check

**Code:** `seashield/engine/spatial.py`, wired in `engine/pipeline.py` and `engine/fusion.py`.
**Measurements:** `python ml/spatial_stats.py`. **Tests:** `tests/test_spatial.py`.

## Method

A hacked buoy can sign any value, so crypto cannot catch it. But it lies alone: a real storm
shows up on the nearby buoys too. Every reading is compared with the recent **accepted**
readings (TRUSTED or CONFIRMED_EVENT) of the other buoys:

- **Shared sensors only.** The network is heterogeneous: SS-B01 has everything, SS-B02 and
  SS-B03 have waves only, SS-B04 has wind and pressure only. Pairs used: waves B01-B02,
  B01-B03, B02-B03; wind B01-B04. Pressure is not compared (see below).
- **Fresh only.** A neighbour reading counts if it was *measured* within 90 min of this one
  (observation time, not wall clock). Hourly network plus the 30 min offset of a forged message.
- **Silent = no opinion.** An offline, stale or sensor-less neighbour gives score `None`, never
  "calm". Storms knock buoys offline: SS-B03 was offline for all of Helene and Milton.
- **Consensus for a spike:** a reading is flagged on a sensor only if it is beyond tolerance
  of **every** fresh neighbour. A storm front reaches buoys hours apart (Helene peaked 4 h later
  at SS-B01 than at SS-B02), so one lagging neighbour cannot condemn a reading.
- **One neighbour is enough for a hidden storm:** if a fresh neighbour reports waves at the
  alert level (6 m) or more and this reading is far below it, the reading is escalated. Missing a
  storm costs more than an operator look.

Score: `0.5 × (gap / tolerance)`, capped at 1. Just beyond the largest real gap gives 0.5
(review); twice it gives 1.0.

## Thresholds, measured on real NOAA data

Metric for waves: `|ln((x + 1) / (y + 1))|`. Real gaps grow with the sea state (5 m apart is
normal in 9 m seas, impossible in 1 m seas), so a ratio fits better than metres. Wind: `|x − y|`
in m/s (the gap does not grow with wind speed). Neighbour values at the same hour and ±1 h.
Tolerance = **maximum on the 2023 training year** (Idalia included), rounded up.

| Sensor | Train 2023 max | Tolerance | Validation 2024-H1 max (beyond) | Helene 2024-09-24..28 max (beyond) |
|---|---|---|---|---|
| Wave height (log ratio) | 1.066 (B01-B03, Idalia) | **1.1** | 0.82 (0 of 39,312 pairs) | 0.76 (0 of 360) |
| Wind speed (m/s) | 12.15 (B01-B04) | **13** | 12.93 (0 of 12,972) | 9.30 (0 of 318) |
| Pressure (hPa) | 26.68 | not used | 7.23 | **41.32 (4 of 318 beyond 27)** |

Per pair (train 2023 max): B01-B02 (322 km) 1.02 · B01-B03 (130 km) 1.07 · B02-B03 (193 km)
0.90. The widest real gap was on the **closest** pair (Idalia's core passed SS-B03), so the
tolerance does not grow with distance: one tolerance per sensor.

Pressure is excluded because the real Helene gap between SS-B01 (953.6 hPa, near the eye) and
SS-B04 reached 41 hPa, far beyond anything in 2023: comparing it would flag the real hurricane.

Attack sizes in the same metric: fake 9 m vs neighbours at 1.5 m → 1.39; calm 1 m vs a 6 m
neighbour → 1.25; calm 1 m vs SS-B02's real Helene peak 8.76 m → 1.59. All beyond 1.1.

## Fusion changes (`engine/fusion.py`)

- **SUPPRESSED_WARNING** (calm here, storm at a fresh neighbour) is checked **before**
  SUSPECTED_FDI: the most dangerous lie is escalated, not just queued for review.
- **CONFIRMED_EVENT** = extreme reading (≥ 6 m), no layer at risk ≥ 0.5, and the wave height
  agrees with at least one fresh neighbour.
- Spatial disagreement counts in the max-risk fusion like physics: score ≥ 0.5 → SUSPECTED_FDI.

## Results

Real data replayed through the full pipeline (signing, crypto, physics, AI, neighbours). Attacks
are injected 30 min after each genuine hourly reading, on a copy of the engine.

| Window | Genuine readings | Spike (+7.5 m) | Suppress (calm 1 m) |
|---|---|---|---|
| Helene 2024-09-25 12:00 → 27 12:00 | 137: **13 CONFIRMED_EVENT** (B01 4, B02 9), 124 TRUSTED, **0 SUSPECTED_FDI, 0 SUPPRESSED_WARNING** | 98/98 SUSPECTED_FDI | 14 SUPPRESSED_WARNING, 22 SUSPECTED_FDI, 62 TRUSTED |
| Calm week 2024-05-06 → 13 | 657: all TRUSTED | 338/338 SUSPECTED_FDI | 338 TRUSTED (undetectable, see below) |

Before this layer a real storm could only be TRUSTED; it is now CONFIRMED_EVENT when a
neighbour agrees. The live suppression test at SS-B01's real Helene peak (7.58 m, 2024-09-26
22:00) is now SUPPRESSED_WARNING → SeaShield alert ESCALATED, with the explanation
"neighbour SS-B02 (322 km) reports wave height 6.6 m; this buoy 1.0 m".

Tests: `pytest` → 57 passed (8 new in `tests/test_spatial.py`: agreement → CONFIRMED_EVENT,
lone spike → SUSPECTED_FDI, one agreeing neighbour is enough, suppress in a storm → ESCALATED,
stale neighbour → no opinion, missing/silent sensor → no opinion, shared sensors only, real
Helene end to end). `ruff check .` → clean.

## Honest limitations

- **Only 4 buoys, 4 usable pairs, one wind pair.** In Helene SS-B03 was offline, so SS-B01's
  waves had a single neighbour (SS-B02, 322 km). With all neighbours offline the layer is silent.
- **Suppress in calm weather stays undetectable** (1.5 m → 1.0 m is plausible everywhere).
  In Helene, 62 of 98 suppressions were TRUSTED: those were hours when the sea was still
  moderate. Suppress is caught when the sea is rough (physics jump) or a neighbour is in a
  storm (this layer).
- **Spikes inside the real band pass.** A fake 6 m next to a real 3 m neighbour (ratio 0.56) is
  within real 2023 gaps. During a storm, a spike on top of a storm is caught by physics, not
  here. Neighbours give corroboration, not precision.
- **Corroboration is "within the largest real gap", not "same value".** A neighbour at 4 m
  corroborates a 6.5 m reading.
- **Tolerances are tight on validation:** wind 12.93 vs 13 m/s. A longer record or the test
  period (not used for tuning) may show genuine gaps beyond them; then the reading goes to an
  operator (SUSPECTED_FDI), it is never deleted.
- **A coordinated attack on several buoys** that agree with each other defeats this layer by
  design (threat model T4 assumes one compromised buoy at a time).
- Pressure, period, direction and water temperature are not compared yet.
