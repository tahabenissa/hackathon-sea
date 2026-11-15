"""Runs one message through every layer in order and returns the Assessment."""

from typing import Any

from pydantic import ValidationError

from seashield.common.registry import Buoy
from seashield.common.schema import Assessment, Evidence, Measurements, Telemetry, Verdict
from seashield.engine.anomaly import AnomalyDetector
from seashield.engine.crypto_gate import CryptoGate
from seashield.engine.fusion import fuse
from seashield.engine.physics import PhysicsChecker
from seashield.engine.spatial import SpatialChecker


class SecurityPipeline:
    def __init__(self, keys: dict[str, bytes], buoys: list[Buoy], replay_window_s: int = 120) -> None:
        self._buoys = buoys
        self.crypto = CryptoGate(keys, window_s=replay_window_s)
        self.physics = PhysicsChecker()
        self.anomaly = AnomalyDetector()
        self.spatial = SpatialChecker(buoys)

    def reset_history(self) -> None:
        """Operator action: forget per-buoy physical history (new replay scenario, maintenance).

        Replay protection (crypto gate sequence numbers and nonces) is deliberately KEPT.
        """
        self.physics = PhysicsChecker()
        self.anomaly.reset()
        self.spatial = SpatialChecker(self._buoys)

    def process(self, raw: dict[str, Any]) -> Assessment:
        buoy_id = str(raw.get("buoy_id"))
        seq = raw.get("seq") if isinstance(raw.get("seq"), int) else -1

        # Verify the RAW dict before any parsing (re-serialising would change the bytes).
        crypto_ev = self.crypto.check(raw)
        if not crypto_ev.passed:
            return fuse(buoy_id, seq, Measurements(), [crypto_ev])

        try:
            msg = Telemetry.model_validate(raw)
        except ValidationError as exc:
            ev = Evidence(layer="crypto", passed=False, score=1.0, detail=f"invalid schema: {exc}")
            return fuse(buoy_id, seq, Measurements(), [ev])

        spatial = self.spatial.assess(msg.buoy_id, msg.observed_at, msg.data)
        evidence = [
            crypto_ev,
            self.physics.check(msg.buoy_id, msg.observed_at, msg.data, sent_at=msg.ts),
            self.anomaly.check(msg.buoy_id, msg.observed_at, msg.data),
            spatial.evidence,
        ]
        result = fuse(msg.buoy_id, msg.seq, msg.data, evidence,
                      neighbours_see_storm=spatial.hidden_storm, corroborated=spatial.corroborated)

        # Only accepted readings become references (for the AI and for neighbours).
        if result.verdict in (Verdict.TRUSTED, Verdict.CONFIRMED_EVENT):
            self.anomaly.commit(msg.buoy_id, msg.observed_at, msg.data)
            self.spatial.update(msg.buoy_id, msg.observed_at, msg.data)
        return result
