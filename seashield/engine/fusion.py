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
# Can the AI score alone send a reading to review? NO, decided from measurements
# (docs/PHASE_D6.md): on the real Hurricane Helene replay it would have held 34 of 137
# genuine readings (Helene was stronger than anything in the 2023 training data), while
# adding ~0 detection on validation. The AI stays ADVISORY: its score is shown, not obeyed.
AI_DECIDES = False
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

    # Any ONE strong piece of evidence is enough to send a reading to human review.
    # (A weighted average let a quiet layer dilute a physics alarm: 0.5 and 0.0 averaged to
    # 0.27, i.e. "trusted". Weights are kept only to order the evidence.)
    scored = [e.score for e in evidence
              if e.layer in WEIGHTS and e.score is not None and (e.layer != "anomaly" or AI_DECIDES)]
    risk = max(scored, default=0.0)

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
    ai = by_layer.get("anomaly")
    if ai is not None and ai.score is not None and ai.score >= SUSPICIOUS_RISK:
        return _assess(buoy_id, seq, Verdict.TRUSTED, risk, evidence,
                       f"Authentic and physically consistent. {ai.detail} (advisory only: "
                       "real storms are unusual too).")
    return _assess(buoy_id, seq, Verdict.TRUSTED, risk, evidence, "All checks passed.")


def _assess(buoy_id: str, seq: int, verdict: Verdict, risk: float,
            evidence: list[Evidence], explanation: str) -> Assessment:
    return Assessment(buoy_id=buoy_id, seq=seq, verdict=verdict, risk=round(risk, 3),
                      evidence=evidence, explanation=explanation)
