# Phase 1: Real Ocean Data (report)

**Date:** 2026-11-14
**Status:** ✅ Complete
**Plan reference:** [`PLAN.md` → Phase 1](PLAN.md#phase-1-real-ocean-data-noaa-ndbc---46-h)
**Detailed findings:** [`data-notes.md`](data-notes.md) · **Decision record:** [`decisions/0003`](decisions/0003-west-florida-cluster-and-time-split.md)

---

## 1. Goal

Get clean, real buoy data from a **cluster of nearby buoys** that includes **real storms**, so
SeaShield can later prove two things: it detects fake data, and it does **not** flag real
storms as attacks.

---

## 2. What was done, step by step

### Step 1: Dependencies
- Added `pyarrow` (parquet files, needed at runtime by the simulator) to the main dependencies
  and `matplotlib` as an optional `ml` extra in `pyproject.toml`.
- `pip install -e ".[dev,ml]"` → pyarrow 26.0.1, matplotlib 3.11.2.

### Step 2: Real station positions
- Downloaded NOAA's official station list
  (`https://www.ndbc.noaa.gov/data/stations/station_table.txt` → `data/raw/meta/`), which gives the
  real name, platform type and lat/lon of every station.
- Chose the **eastern Gulf of Mexico** as the search area because several 2023–2024 tropical
  cyclones crossed it. 11 candidate stations.

### Step 3: Download 3 years of history
```powershell
python ml/download_ndbc.py <station> 2023 2024 2025
```
- 29 files downloaded (101–732 KB each). 4 not available: 42003 (2023–2025) and 42039 (2024–2025)
  returned HTTP 404.

### Step 4: Implement the cleaner (`ml/clean.py`)
- Parses the NDBC format (header + units line), builds UTC timestamps.
- Replaces missing-value sentinels **per column** (99 / 999 / 9999). 999 is a valid
  pressure, so a global replace would have deleted real storm data.
- Resamples to hourly; wind direction averaged as a vector.
- Interpolates only short gaps (≤ 2 h).
- Writes `data/processed/<station>.parquet` + `<station>_quality.json`.
- Bug hit on the first run: pandas 3 returns read-only arrays (copy-on-write) → fixed with an explicit copy.

### Step 5: Survey all candidates (`ml/survey.py`, new)
- One command cleans every candidate and prints completeness per field, wave statistics and
  pairwise distances. Main results:

| Station | Measures | Wave max (time) |
|---|---|---|
| 42036 West Tampa | everything; ≤ 0.2 % missing (except water temp) | 7.58 m (2024-09-26 22:00) |
| 42097 Pulley Ridge | waves only | 8.76 m (2024-09-26 18:00) |
| 42099 Offshore St. Petersburg | waves only | 9.98 m (2023-08-30 01:00) |
| 42013 C10 | wind/pressure, no waves | n/a |
| 42022 C12 | wind/pressure, no waves | n/a |
| others | see `data-notes.md` | |

### Step 6: Identify real storms from the data
- Listed the largest daily events per station (events separated by at least 4 days) and found events
  shared by several stations: 2023-08-30, 2024-08-04, 2024-09-26, 2024-10-09 (dates matching
  Idalia, Debby, Helene, Milton) plus winter fronts.
- Checked **coverage during each storm**. 42022 had **0 %** data in every hurricane → rejected.

### Step 7: Choose the cluster → `config/buoys.yaml`
| ID | Station | Sensors |
|---|---|---|
| SS-B01 | 42036 West Tampa | all |
| SS-B02 | 42097 Pulley Ridge | waves, period, water temp |
| SS-B03 | 42099 Offshore St. Petersburg | waves, period, water temp |
| SS-B04 | 42013 C10 | wind, wind dir, pressure, water temp |

- Added a **`sensors`** field to the registry (`seashield/common/registry.py`) and a `sensors`
  column to the `buoys` table (`infra/postgres/init.sql`): the network is heterogeneous.

### Step 8: Explore (`ml/explore.py`, new)
- Produces `docs/assets/phase1/stats.json` + 5 figures: normal week, Idalia, Helene, Milton,
  waves vs wind.
- Computes coverage, outages, neighbour agreement, hourly-change percentiles, event table, and
  runs the **current physics rules over all real data**.

### Step 9: Bug found by looking at the plot → fixed + tested
- The Idalia plot showed 42099 flat at ~10 m for 3 hours. The raw file showed the buoy actually
  **stopped transmitting** after 9.63 m at 01:56 (and stayed silent until 2023-10-06).
- Cause: pandas `interpolate(limit=2)` fills the first 2 steps of **any** gap, even a 37-day one,
  which **invented data**.
- Fix: `interpolate_short_gaps()` fills a gap only if the whole gap is ≤ 2 h.
- New tests `tests/test_clean.py` (4): per-column sentinels (999 hPa kept), short vs long gap,
  no extrapolation, vector wind-direction mean.

### Step 10: Documentation
- `docs/data-notes.md`: all real numbers (sections: cluster, quality, outages, events,
  neighbours, change rates, physics check, split, cleaning rules).
- `docs/decisions/0003-west-florida-cluster-and-time-split.md`.

---

## 3. Key findings (all measured)

1. **SS-B01 never went offline**: 99.8–99.9 % coverage for waves, wind and pressure, through
   every storm. Helene at SS-B01: **7.58 m waves, 28.2 m/s wind, 953.6 hPa**.
2. **Storms knock buoys offline**: SS-B03 was offline during Idalia (37 days) and from
   2024-08-28 to 11-25 (Helene + Milton). SS-B02 went offline for 115 days right after Milton.
   → Design rule: **a silent neighbour is not evidence of calm.**
3. **Neighbours agree, and less so with distance**: correlation 0.915 at 130 km, 0.763 at 322 km;
   99 % of differences ≤ 0.79 m at 130 km. A fake 9 m reading among real 1.7 m readings stands out clearly.
4. **Storms move across the network**: in Helene the southern buoy peaked **4 h** before the
   northern one. Cross-buoy checks must allow for the lag.
5. **Real wave height changes slowly**: 99.9 % of hourly changes ≤ 0.62 m (SS-B01).
6. **Current physics rules: 0 false alarms on 94,458 real hours, including all storms.**
7. **Design problem found**: the rate rule uses send time `ts`. Under fast replay it would flag
   0.70–1.05 % of real hours (mostly in storms); with true hourly timing it is too loose to catch
   a 1.5 → 9 m jump. → Add signed **`observed_at`** in Phase 2; recalibrate rates in Phase 5.1.

---

## 4. Time split decided

| Part | Period | Real events |
|---|---|---|
| Train | 2023 | Idalia, Dec 2023 front |
| Validation | 2024-01 → 2024-06 | winter fronts |
| Test | 2024-07 → 2025-12 | **Debby, Helene, Milton** |

---

## 5. Results

| Check | Result |
|---|---|
| Buoy cluster chosen with real positions | ✅ 4 buoys, 130–322 km apart |
| `config/buoys.yaml` filled | ✅ station, lat, lon, sensors |
| Raw data downloaded | ✅ 29 files (2023–2025) |
| `ml/clean.py` implemented + tested | ✅ |
| Processed data | ✅ `data/processed/{42036,42097,42099,42013}.parquet` (git-ignored) |
| Real storms identified | ✅ Idalia, Debby, Helene, Milton (+ fronts) |
| Exploration figures + stats | ✅ `docs/assets/phase1/` |
| Train/validation/test split | ✅ defined |
| Tests | ✅ **27 passed**, ruff clean |
| Money spent | **$0** |

---

## 6. Differences from the plan

- The plan suggested a Jupyter notebook; I wrote **`ml/explore.py`** instead, so the figures
  and numbers can be regenerated with one command and checked in review.
- Extra tool **`ml/survey.py`** to compare candidate stations objectively.
- Extra: the `sensors` field (heterogeneous network) and the `observed_at` decision, both driven by
  what the data showed.

---

## 7. How to reproduce

```powershell
.venv\Scripts\activate
pip install -e ".[dev,ml]"
foreach ($s in "42036","42097","42099","42013") { python ml/download_ndbc.py $s 2023 2024 2025 }
python ml/clean.py 42036 42097 42099 42013
python ml/explore.py          # → docs/assets/phase1/
pytest
```
(Optional) full candidate survey: download the other stations too, plus
`data/raw/meta/station_table.txt`, then `python ml/survey.py <stations…>`.

---

## 8. Next: Phase 2 (simulator + MQTT)

1. Add signed `observed_at` to `Telemetry`; simulator sets it from the historical timestamp.
2. Implement `seashield/simulator/replay.py` (parquet → `Measurements`, NaN → `None`,
   only the buoy's own `sensors`).
3. Time-based starting `seq` (restart-safe), `--start` option to jump to a calm day or a storm.
4. Mosquitto via Docker; engine + simulator end to end.
