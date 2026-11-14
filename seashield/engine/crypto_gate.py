"""Layer 1: authentication, integrity and replay protection (hard rules).

Catches threats T1 (tampering in transit), T2 (fake device), T3 (replay).
Cannot catch T4 (compromised buoy with a valid key): later layers handle that.
"""

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from seashield.common import signing
from seashield.common.schema import Evidence


@dataclass
class _BuoyState:
    last_seq: int = -1
    nonce_order: deque[str] = field(default_factory=deque)
    nonces: set[str] = field(default_factory=set)


class CryptoGate:
    def __init__(
        self,
        keys: dict[str, bytes],
        window_s: int = 120,
        nonce_cache_size: int = 2048,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._keys = keys
        self._window_s = window_s
        self._nonce_cache_size = nonce_cache_size
        self._clock = clock
        self._state: dict[str, _BuoyState] = {}

    def check(self, raw: dict[str, Any]) -> Evidence:
        """Check one parsed message. State is only updated when every check passes."""
        buoy_id = raw.get("buoy_id")
        key = self._keys.get(buoy_id) if isinstance(buoy_id, str) else None
        if key is None:
            return self._fail(f"unknown device '{buoy_id}'")

        if not signing.verify(raw, key):
            return self._fail("signature invalid: message altered or not signed by this buoy")

        try:
            ts = datetime.fromisoformat(str(raw["ts"]))  # Python 3.11+ accepts the "Z" suffix
            seq = int(raw["seq"])
            nonce = str(raw["nonce"])
        except (KeyError, ValueError) as exc:
            return self._fail(f"malformed message: {exc}")

        if ts.tzinfo is None:
            return self._fail("timestamp has no timezone")
        age = abs((self._clock() - ts).total_seconds())
        if age > self._window_s:
            return self._fail(f"timestamp {age:.0f}s off (window {self._window_s}s): possible replay")

        state = self._state.setdefault(buoy_id, _BuoyState())
        if seq <= state.last_seq:
            return self._fail(f"sequence {seq} <= last {state.last_seq}: replay")
        if nonce in state.nonces:
            return self._fail("nonce already used: replay")

        state.last_seq = seq
        state.nonces.add(nonce)
        state.nonce_order.append(nonce)
        if len(state.nonce_order) > self._nonce_cache_size:
            state.nonces.discard(state.nonce_order.popleft())

        return Evidence(layer="crypto", passed=True, score=0.0, detail="authentic, fresh, in order")

    @staticmethod
    def _fail(detail: str) -> Evidence:
        return Evidence(layer="crypto", passed=False, score=1.0, detail=detail)
