"""Risk fusion: combine per-layer evidence into one verdict + human explanation.

Rules (see SEASHIELD_AI_MASTER_PROMPT.md, section 4):
  - crypto failure                         -> REJECTED (hard rule)
  - extreme reading, corroborated          -> CONFIRMED_EVENT (real storm: let the alert through)
  - extreme reading, not corroborated      -> SUSPECTED_FDI (hold alert for an operator)
  - calm reading while neighbours see storm -> SUPPRESSED_WARNING (escalate: fail safe)
Weights and thresholds are initial values, to be tuned in Phase 6.
"""

from seashield.common.schema import Assessment, Evidence, Measurements, Verdict

WEIGHTS = {"physics": 0.4, "anomaly": 0.35, "spatial": 0.25}
SUSPICIOUS_RISK = 0.5
EXTREME_WAVES_M = 6.0


def fuse(
    buoy_id: str,
    seq: int,
    m: Measurements,
    evidence: list[Evidence],
    neighbours_see_storm: bool = False,
) -> Assessment:
    by_layer = {e.layer: e for e in evidence}

    crypto = by_layer.get("crypto")
    if crypto is not None and not crypto.passed:
        return _assess(buoy_id, seq, Verdict.REJECTED, 1.0, evidence, f"Rejected: {crypto.detail}.")

    scored = [(WEIGHTS[e.layer], e.score) for e in evidence if e.layer in WEIGHTS and e.score is not None]
    total_w = sum(w for w, _ in scored)
    risk = sum(w * s for w, s in scored) / total_w if total_w else 0.0

    extreme = m.wave_height_m is not None and m.wave_height_m >= EXTREME_WAVES_M
    reasons = "; ".join(e.detail for e in evidence if not e.passed)

    if extreme and risk < SUSPICIOUS_RISK and neighbours_see_storm:
        return _assess(buoy_id, seq, Verdict.CONFIRMED_EVENT, risk, evidence,
                       "Extreme reading corroborated by physics and neighbours: real event.")
    if risk >= SUSPICIOUS_RISK:
        return _assess(buoy_id, seq, Verdict.SUSPECTED_FDI, risk, evidence,
                       f"Authentic but implausible, alert held for operator review: {reasons}.")
    if not extreme and neighbours_see_storm:
        return _assess(buoy_id, seq, Verdict.SUPPRESSED_WARNING, max(risk, SUSPICIOUS_RISK), evidence,
                       "Calm reading while neighbours report a storm: possible hidden danger, escalated.")
    return _assess(buoy_id, seq, Verdict.TRUSTED, risk, evidence, "All checks passed.")


def _assess(buoy_id: str, seq: int, verdict: Verdict, risk: float,
            evidence: list[Evidence], explanation: str) -> Assessment:
    return Assessment(buoy_id=buoy_id, seq=seq, verdict=verdict, risk=round(risk, 3),
                      evidence=evidence, explanation=explanation)
