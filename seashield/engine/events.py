"""What the engine publishes for every message: the evidence AND both alert decisions.

Same message, two monitoring centres:
  - unprotected centre: trusts everything, alerts above 6 m (engine/baseline.py)
  - SeaShield centre:   alerts only on verified data, holds suspicious alerts for a human
"""

from datetime import UTC, datetime
from typing import Any

from seashield.common.schema import Assessment, Verdict
from seashield.engine.baseline import WAVE_ALERT_M

# SeaShield alert states
ISSUED = "ISSUED"          # high waves on verified data: warning goes out
HELD = "HELD"              # high waves on authentic but implausible data: operator decides
BLOCKED = "BLOCKED"        # high waves in a forged/replayed message: never reaches the alert system
ESCALATED = "ESCALATED"    # possible hidden danger: escalated to the operator
REVIEW = "REVIEW"          # suspicious low reading: real conditions unknown -> operator review


def seashield_alert(verdict: Verdict, wave_height_m: float | None) -> str | None:
    if verdict == Verdict.SUPPRESSED_WARNING:
        return ESCALATED
    high = wave_height_m is not None and wave_height_m > WAVE_ALERT_M
    if verdict == Verdict.SUSPECTED_FDI:
        # Fail safe: a suspicious CALM reading may be hiding a storm, so never just ignore it.
        return HELD if high else REVIEW
    if not high:
        return None
    if verdict == Verdict.REJECTED:
        return BLOCKED
    return ISSUED  # TRUSTED / CONFIRMED_EVENT


def build_event(raw: dict[str, Any], result: Assessment, unprotected_alert: str | None) -> dict:
    data = raw.get("data") if isinstance(raw.get("data"), dict) else {}
    wave = data.get("wave_height_m")
    return {
        "buoy_id": result.buoy_id,
        "seq": result.seq,
        "observed_at": raw.get("observed_at"),
        "received_at": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "data": data,
        "verdict": result.verdict.value,
        "risk": result.risk,
        "evidence": [e.model_dump() for e in result.evidence],
        "explanation": result.explanation,
        "unprotected_alert": unprotected_alert,
        "seashield_alert": seashield_alert(result.verdict, wave if isinstance(wave, (int, float)) else None),
    }
