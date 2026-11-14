"""Data contract: what a buoy sends and what the security engine answers."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Measurements(BaseModel):
    """One set of readings. Any field may be missing (sensor offline)."""

    wave_height_m: float | None = None
    dominant_period_s: float | None = None
    wind_speed_ms: float | None = None
    wind_dir_deg: float | None = None
    pressure_hpa: float | None = None
    water_temp_c: float | None = None


class Telemetry(BaseModel):
    """Message published by a buoy on seashield/buoys/{buoy_id}/telemetry.

    `sig` = hex HMAC-SHA256 over the canonical JSON of every other field
    (see seashield.common.signing).

    Two clocks, two jobs (decision 0003):
      - `ts`          = when the message was SENT  -> replay protection (crypto gate)
      - `observed_at` = when the sea was MEASURED  -> physics rate checks
    In live operation they are seconds apart; in replay mode `observed_at` is the
    historical NOAA timestamp while `ts` is "now".
    """

    buoy_id: str
    seq: int = Field(ge=0, description="Monotonic per-buoy sequence number")
    ts: datetime = Field(description="Send time, UTC")
    observed_at: datetime = Field(description="Measurement time, UTC")
    nonce: str = Field(description="Random value, unique per message")
    data: Measurements
    sig: str = ""


class Verdict(StrEnum):
    TRUSTED = "TRUSTED"
    REJECTED = "REJECTED"                      # crypto / replay failure (hard)
    SUSPECTED_FDI = "SUSPECTED_FDI"            # authentic but implausible
    CONFIRMED_EVENT = "CONFIRMED_EVENT"        # extreme but corroborated (real storm)
    SUPPRESSED_WARNING = "SUPPRESSED_WARNING"  # calm reading while neighbours see danger


class Evidence(BaseModel):
    """Output of one layer of the security engine."""

    layer: str                     # "crypto" | "physics" | "anomaly" | "spatial"
    passed: bool
    score: float | None = None     # 0 = normal ... 1 = very suspicious; None = no opinion
    detail: str = ""


class Assessment(BaseModel):
    """Final decision for one message, with the evidence behind it."""

    buoy_id: str
    seq: int
    verdict: Verdict
    risk: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence]
    explanation: str
