# D6: AI anomaly layer (report)

**Date:** 2026-11-15 · **Status:** ✅ Implemented, running **advisory** (decision measured, see §3)

## 1. What was built
- `ml/train.py`: one **Isolation Forest per buoy** (200 trees, standardized features),
  trained only on **real 2023 data** (Hurricane Idalia included, no attack data).
  Per-buoy features follow the buoy's real sensors (`seashield/engine/features.py`):

| Buoy | Features | Training rows |
|---|---|---|
| SS-B01 | waves, period, wind, pressure + hourly rates of waves, wind, pressure | 8,194 |
| SS-B02 | waves, period, rate of waves | 7,316 |
| SS-B03 | waves, period, rate of waves | 7,511 |
| SS-B04 | wind, pressure + their hourly rates | 8,700 |

- `seashield/engine/anomaly.py`: live scoring of every reading, with the top-2 reasons in
  σ (e.g. *"wave_height_m +8.3σ, rate_wave_height_m +7.9σ"*). Score calibrated on the training
  year: 0.5 = as rare as the rarest 0.1 % of 2023 readings. Only accepted readings become
  the reference for the next one.
- `ml/evaluate.py`: replays real held-out data through physics + AI with seeded injected
  compromised-buoy readings (+0.5 … +7.5 m waves, or m/s wind for SS-B04).

## 2. Measured results (validation = Jan–Jun 2024, never used for training)
| | Physics (data-derived rules) | AI (Isolation Forest) |
|---|---|---|
| False alarms on 17,428 real readings | **0** | 6 (0.03 %) |
| Detection of +4 m / +7.5 m fakes | **76.8 % / 74.3 %** | 1.4 % / 1.4 % |
| Detection of +0.5 / +1 / +2 m fakes | 0 % | 0 % |

The ~25 % physics misses at +4/+7.5 are SS-B04, where the fake is added to **wind**
(+7.5 m/s is below the 15 m/s per hour limit). Source: `docs/assets/eval/validation.json`.

**Why the AI is weak here:** Isolation Forest isolates a point by splitting random features.
A fake that changes 1–2 features among 3–7 normal ones is diluted, so its score stays close
to normal readings. The first calibration (alarm at the 2023 maximum) caught almost nothing;
moving the alarm to the 2023 p99.9 (training data only) did not change detection.

## 3. Decision: the AI is advisory (measured, not assumed)
With the AI allowed to hold alerts on its own, the **real Hurricane Helene replay**
(2024-09-25 12:00 → 09-27 12:00, 137 genuine messages) gave **34 SUSPECTED_FDI on genuine
data**. Helene (954 hPa, 8.8 m waves) was stronger than anything in the 2023 training year,
so "unusual" ≠ "attack". Holding real hurricane warnings is the worst possible failure for
a warning system.

→ `fusion.AI_DECIDES = False`: the AI score is computed and **shown** for every reading
(e.g. during Helene: *"Authentic and physically consistent. AI: rarer than 99.9 % of real
2023 readings … (advisory only: real storms are unusual too)"*), but the decision rests on
crypto + physics. With this setting the Helene replay gives 0 suspected and 0 rejected
(`tests/test_replay.py`).

Also fixed: fusion used a **weighted average**, which let a quiet layer dilute a physics
alarm (0.5 and 0.0 averaged to 0.27, i.e. "trusted"). Now any one strong piece of evidence
sends the reading to review.

## 4. Honest limitations and next steps
- Small fakes (≤ 2 m) are not detected by any layer yet. The **neighbour check** is the right
  tool (99 % of real differences between SS-B01 and SS-B03 are ≤ 0.79 m, `data-notes.md` §4).
- A better ML model for this job: a **residual model** (predict each reading from the buoy's
  own recent history + its other sensors + neighbours; flag large surprises), trained on
  multi-year data that includes hurricanes.
- The test-period evaluation (`--part test`, 2024-07 → 2025-12) was run once afterwards
  (10 min 42 s, nothing tuned after seeing it): results in [`evaluation.md`](evaluation.md) §4
  and `assets/eval/test.json`.
