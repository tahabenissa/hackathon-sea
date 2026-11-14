# Data notes: SeaShield buoy cluster

> Every number in this file was produced by `ml/survey.py` and `ml/explore.py` on real NOAA
> NDBC data (raw output: `docs/assets/phase1/stats.json`). Nothing here is estimated by hand.

**Source:** NOAA National Data Buoy Center (NDBC), historical *standard meteorological* (stdmet)
files, https://www.ndbc.noaa.gov/. US government data; cite *"NOAA National Data Buoy Center"*.
**Period downloaded:** 2023-01-01 → 2025-12-31 (3 years, hourly after cleaning = 26,304 hours per station).

---

## 1. The cluster: West Florida Shelf, eastern Gulf of Mexico

| SeaShield ID | NDBC | Name (NDBC station table) | Lat, Lon | Platform | Sensors used |
|---|---|---|---|---|---|
| SS-B01 | 42036 | West Tampa, 112 NM WNW of Tampa | 28.500, −84.505 | 3-m discus buoy | waves, period, wind, wind dir, pressure, water temp |
| SS-B02 | 42097 | Pulley Ridge, FL | 25.704, −83.654 | Waverider buoy | waves, period, water temp |
| SS-B03 | 42099 | Offshore St. Petersburg, FL | 27.352, −84.275 | Waverider buoy | waves, period, water temp |
| SS-B04 | 42013 | C10, WFS Central Buoy, 25 m isobath | 27.173, −82.924 | Offshore buoy | wind, wind dir, pressure, water temp |

**Distances (km):** B01–B03 **130** · B03–B04 **135** · B02–B04 **179** · B02–B03 **193** ·
B01–B04 **214** · B01–B02 **322**

**Why this cluster:** it was hit by several tropical cyclones in 2023–2024 that appear clearly in
the data, SS-B01 has near-complete data through every storm, and the stations are close enough
to see the same weather.

**The network is heterogeneous** (as in reality): wave-only Waveriders, a met-only buoy, and one
full-sensor buoy. Cross-buoy checks must compare **only the fields both buoys measure**.

### Candidates rejected (from the survey)
| Station | Reason |
|---|---|
| 42003 East Gulf | No data files for 2023–2025 (HTTP 404) |
| 42039 Pensacola | Only 2023 available |
| 42022 C12 | 0 % data during all four 2023–2024 hurricane windows |
| 42023 C13 | No waves; 20–21 % missing wind/pressure |
| 42040, 42012, 42001 | Complete sensors, but far from the others (342–583 km from 42036) and weak storms (max waves 3.96–5.44 m) |

---

## 2. Data quality (after cleaning, hourly)

Coverage = % of hours with a value.

| Buoy | Waves | Period | Wind | Pressure | Water temp |
|---|---|---|---|---|---|
| SS-B01 (42036) | **99.9** | 94.8 | **99.8** | **99.8** | 50.6 |
| SS-B02 (42097) | 73.8 | 71.6 | n/a | n/a | 73.8 |
| SS-B03 (42099) | 88.4 | 86.1 | n/a | n/a | 88.4 |
| SS-B04 (42013) | n/a | n/a | 97.0 | 97.0 | 95.0 |

### Outages of 3 days or more
| Buoy | Outages |
|---|---|
| SS-B01 | none |
| SS-B02 | 2023-07-07→08-11 (35 d) · 2023-09-14→09-22 (8 d) · **2024-10-10→2025-02-02 (115 d, right after Milton)** · 2025-07-13→08-14 (32 d) · 2025-09-24→12-26 (93 d) |
| SS-B03 | **2023-08-30→10-06 (37 d, during Idalia)** · **2024-08-28→11-25 (89 d, covers Helene and Milton)** |
| SS-B04 | **2024-10-09→10-22 (12 d, Milton)** |

**Finding:** storms knock buoys offline. Design rule for the engine: **a silent neighbour is
not evidence of calm.** Missing data must be "no opinion", never "normal".

**Example:** during Idalia, 42099 sent 7.07 m (00:26), **10.32 m** (01:26), 9.63 m (01:56) on
2023-08-30, then nothing until 2023-10-06.

---

## 3. Real extreme events in the data

The dates coincide with named tropical cyclones. Verify against the NHC Tropical Cyclone
Reports before citing names in slides.

| Event (window) | SS-B01 waves / wind / min pressure | SS-B02 waves | SS-B03 waves | SS-B04 wind / min pressure |
|---|---|---|---|---|
| **Idalia** (2023-08-28→09-01) | 6.28 m / 23.7 m/s / 975.2 hPa | 6.06 m | 9.98 m (42 % coverage) | 17.9 m/s / 1001.5 hPa |
| Winter front (2023-12-15→19) | 5.31 m / 20.9 m/s / 998.6 hPa | 3.75 m | 4.97 m | 14.0 m/s / 999.2 hPa |
| **Debby** (2024-08-02→06) | 4.38 m / 19.7 m/s / 997.8 hPa | 3.17 m | 4.27 m | 19.5 m/s / 1004.8 hPa |
| **Helene** (2024-09-24→28) | **7.58 m / 28.2 m/s / 953.6 hPa** | **8.76 m** | offline | 23.3 m/s / 991.6 hPa |
| **Milton** (2024-10-07→11) | 5.48 m / 19.8 m/s / 998.8 hPa | 8.12 m (62 % coverage) | offline | 16.5 m/s / 993.2 hPa |

**Storm propagation:** in Helene, SS-B02 (south) peaked at 2024-09-26 18:00 UTC and SS-B01
(north) at 22:00 UTC: **4 h later**. Cross-buoy checks must allow for this lag.

Figures: `docs/assets/phase1/event_idalia.png`, `event_helene.png`, `event_milton.png`,
`normal_week.png`.

---

## 4. How neighbours relate (wave height, hourly)

| Pair | Distance | Overlap hours | Correlation | Median abs diff | p95 abs diff | p99 abs diff |
|---|---|---|---|---|---|---|
| SS-B01–SS-B03 | 130 km | 23,209 | **0.915** | 0.13 m | 0.53 m | 0.79 m |
| SS-B02–SS-B03 | 193 km | 17,692 | 0.867 | 0.15 m | 0.65 m | 1.09 m |
| SS-B01–SS-B02 | 322 km | 19,403 | 0.763 | 0.22 m | 0.88 m | 1.47 m |

**Meaning:** agreement drops with distance, which supports a tolerance that grows with distance.
A fake 9 m reading next to real 1.7–1.8 m neighbours is a difference of over 7 m. Even
the most distant pair differs by more than 1.47 m only 1 % of the time.

---

## 5. How fast real values change (|Δ| between consecutive hours)

| Buoy | Field | p50 | p99 | p99.9 | max |
|---|---|---|---|---|---|
| SS-B01 | wave height (m) | 0.03 | 0.305 | 0.624 | 1.32 |
| SS-B02 | wave height (m) | 0.03 | 0.27 | 0.589 | 1.385 |
| SS-B03 | wave height (m) | 0.025 | 0.27 | 0.48 | 2.905 |
| SS-B01 | wind speed (m/s) | 0.417 | 2.883 | 5.312 | 8.817 |
| SS-B04 | wind speed (m/s) | 0.45 | 3.376 | 5.978 | 11.8 |
| SS-B01 | pressure (hPa) | 0.3 | 1.24 | 2.729 | **15.35** (Helene) |
| SS-B04 | pressure (hPa) | 0.3 | 1.15 | 1.9 | 5.4 |
| SS-B01 | water temp (°C) | 0.033 | 0.3 | 0.574 | 1.067 |

Wave–wind relation at SS-B01: `docs/assets/phase1/wave_vs_wind_42036.png`. Waves above 4 m
appear only with wind of roughly 7 m/s or more (or with long-period swell), which supports the
wind–sea consistency rule.

---

## 6. Current physics heuristics vs real data

`engine/physics.py` (initial heuristics) run on all real hourly data with **true hourly
timestamps**:

| Buoy | Hours checked | Flagged |
|---|---|---|
| SS-B01 | 26,287 | **0** |
| SS-B02 | 19,424 | **0** |
| SS-B03 | 23,242 | **0** |
| SS-B04 | 25,505 | **0** |

No false alarms on 3 years of real data, **including all storms**. But this reveals two problems
for later phases:

1. **Rules are too loose for hourly data.** `MAX_RATE_PER_MIN["wave_height_m"] = 0.3` is
   18 m per hour, so a fake 1.5 → 9.0 m jump between two hourly readings would **not** trip the
   rate rule. Real data says p99.9 = 0.62 m/h (max 2.9 m/h).
2. **Timing bug in the design.** The rate rule uses the message *send* time (`ts`). The
   simulator replays one historical hour every ~2 s, so the elapsed time is clamped to 1 minute.
   Real hourly changes above 0.3 m would then be flagged: **276 hours at SS-B01 (1.05 %), 145 at
   SS-B02 (0.75 %), 162 at SS-B03 (0.70 %)**, concentrated in storms.

**Decision:** add a signed **`observed_at`** field (measurement time) to the message in Phase 2;
physics rates use `observed_at`, while replay protection keeps using `ts`. Recalibrate the rate
limits **per hour** in Phase 5.1 using the table in section 5.

---

## 7. Time split (no shuffling)

| Part | Period | Real events inside | Use |
|---|---|---|---|
| **Train** | 2023-01-01 → 2023-12-31 | Idalia, Dec 2023 front | Fit Isolation Forest; calibrate physics thresholds; verify Idalia is NOT flagged |
| **Validation** | 2024-01-01 → 2024-06-30 | winter fronts only (≈4–4.5 m) | Tune fusion weights / thresholds |
| **Test** | 2024-07-01 → 2025-12-31 | **Debby, Helene, Milton** | Final evaluation only (Phase 6), never used for tuning |

The training data contains **natural storms** on purpose: it is real, unattacked data, and the
model must learn that storms are part of normal ocean behaviour. Attacks are only injected
into copies of validation/test data.

**Limitations:** only one hurricane in train; validation has no hurricane; 2025 has no tropical
event in this cluster (largest waves ≈ 4 m); SS-B03 is offline for Helene and Milton.

---

## 8. Cleaning rules (ml/clean.py)

- Missing-value sentinels replaced **per column**: WVHT/DPD/WSPD = 99, WDIR/WTMP = 999,
  PRES = 9999. (999 hPa is a valid stormy pressure and is kept; tested.)
- Resampled to **1 hour** (waves are reported hourly; met data every 10 min at some stations).
- Wind direction averaged as a **vector** (350° and 10° give 0°, not 180°).
- Gaps filled by linear interpolation **only if the whole gap is ≤ 2 hours**. Long gaps stay
  NaN; no extrapolation after the last value. (A first version used pandas `limit=2`, which
  invented 2 hours of ~10 m waves after 42099 went offline in Idalia. Caught in the plot,
  fixed and tested.)
