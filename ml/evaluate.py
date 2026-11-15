"""Evaluate the detection layers on REAL held-out data with injected, labelled attacks.

Usage:  python ml/evaluate.py [--part validation|test]
Writes: docs/assets/eval/<part>.json  (all numbers in the docs come from here)

Method (no shuffling, nothing tuned on the test part):
  1. Replay every buoy's real readings of the chosen period, in time order, through the
     physics layer and the AI layer (crypto is tested separately: forged messages are
     always rejected by construction, see tests/test_crypto_gate.py).
  2. "Real" rows = genuine readings -> any flag is a FALSE POSITIVE.
  3. "Attack" rows = for a seeded random sample of real hours, a compromised-buoy reading
     is built from the genuine one (+X m on wave height, or wind for SS-B04) and judged
     against the same history -> a flag is a DETECTION. The fake is never committed.
"""

import argparse
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from seashield.common.registry import load_buoys
from seashield.common.schema import Measurements
from seashield.engine.anomaly import AnomalyDetector
from seashield.engine.physics import PhysicsChecker

ROOT = Path(__file__).resolve().parents[1]
PARTS = {"validation": ("2024-01-01", "2024-06-30"), "test": ("2024-07-01", "2025-12-31")}
STORMS = {"Debby": ("2024-08-02", "2024-08-06"), "Helene": ("2024-09-24", "2024-09-28"),
          "Milton": ("2024-10-07", "2024-10-11")}
MAGNITUDES_M = [0.5, 1.0, 2.0, 4.0, 7.5]   # added to the real wave height (or wind, m/s, for SS-B04)
ATTACK_RATE = 0.02                        # 2 % of real hours get a fake twin
AI_THRESHOLD = 0.5


def run(part: str) -> dict:
    start, end = PARTS[part]
    rng = np.random.default_rng(42)
    ai = AnomalyDetector(ROOT / "models" / "isolation_forest.joblib")
    out: dict = {"part": part, "period": [start, end], "buoys": {}}

    for b in load_buoys(ROOT / "config" / "buoys.yaml"):
        df = pd.read_parquet(ROOT / "data" / "processed" / f"{b.ndbc_station}.parquet").loc[start:end]
        df = df[[s for s in b.sensors if s in df.columns]]
        target = "wave_height_m" if "wave_height_m" in b.sensors else "wind_speed_ms"
        phys = PhysicsChecker()
        real = {"n": 0, "phys": 0, "ai": 0, "either": 0, "storm_n": 0, "storm_phys": 0, "storm_ai": 0}
        att = {m: {"n": 0, "phys": 0, "ai": 0, "either": 0} for m in MAGNITUDES_M}
        storm_mask = pd.Series(False, index=df.index)
        for s0, s1 in STORMS.values():
            storm_mask |= (df.index >= s0) & (df.index <= s1)

        for ts, row in df.iterrows():
            values = {k: float(v) for k, v in row.items() if pd.notna(v)}
            if not values:
                continue
            t = ts.to_pydatetime()
            m = Measurements(**values)

            # ---- attack twin, judged BEFORE the genuine reading is committed
            if target in values and rng.random() < ATTACK_RATE:
                mag = MAGNITUDES_M[int(rng.integers(len(MAGNITUDES_M)))]
                fake = m.model_copy(update={target: values[target] + mag})
                probe = PhysicsChecker()
                probe._last = dict(phys._last)            # same history, never committed
                p_fail = not probe.check(b.buoy_id, t - timedelta(minutes=30), fake).passed
                a_ev = ai.check(b.buoy_id, t - timedelta(minutes=30), fake)
                a_fail = a_ev.score is not None and a_ev.score >= AI_THRESHOLD
                a = att[mag]
                a["n"] += 1
                a["phys"] += p_fail
                a["ai"] += a_fail
                a["either"] += p_fail or a_fail

            # ---- genuine reading
            p_ev = phys.check(b.buoy_id, t, m)
            a_ev = ai.check(b.buoy_id, t, m)
            p_fail = not p_ev.passed
            a_fail = a_ev.score is not None and a_ev.score >= AI_THRESHOLD
            real["n"] += 1
            real["phys"] += p_fail
            real["ai"] += a_fail
            real["either"] += p_fail or a_fail
            if storm_mask.loc[ts]:
                real["storm_n"] += 1
                real["storm_phys"] += p_fail
                real["storm_ai"] += a_fail
            if p_ev.passed:
                ai.commit(b.buoy_id, t, m)
        out["buoys"][b.buoy_id] = {"attacked_field": target, "real": real, "attacks": att}

    # totals
    tot_real = {k: sum(v["real"][k] for v in out["buoys"].values()) for k in
                ("n", "phys", "ai", "either", "storm_n", "storm_phys", "storm_ai")}
    tot_att = {m: {k: sum(v["attacks"][m][k] for v in out["buoys"].values())
                   for k in ("n", "phys", "ai", "either")} for m in MAGNITUDES_M}
    out["totals"] = {"real": tot_real, "attacks": tot_att}
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--part", choices=list(PARTS), default="validation")
    args = p.parse_args()
    res = run(args.part)
    path = ROOT / "docs" / "assets" / "eval" / f"{args.part}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(res, indent=2, default=str))

    r = res["totals"]["real"]
    print(f"[{args.part}] real readings: {r['n']}  false positives: physics {r['phys']}  "
          f"AI {r['ai']}  either {r['either']}  ({100 * r['either'] / max(r['n'], 1):.2f} %)")
    print(f"           storm hours: {r['storm_n']}  flagged: physics {r['storm_phys']}  AI {r['storm_ai']}")
    for mag, a in res["totals"]["attacks"].items():
        n = max(a["n"], 1)
        print(f"  attack +{mag:<4} n={a['n']:4}  physics {100 * a['phys'] / n:5.1f} %  "
              f"AI {100 * a['ai'] / n:5.1f} %  either {100 * a['either'] / n:5.1f} %")
    print(f"saved {path}")


if __name__ == "__main__":
    main()
