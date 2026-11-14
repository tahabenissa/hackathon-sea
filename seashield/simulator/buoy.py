"""One virtual buoy: holds its key and sequence counter, builds signed messages."""

import time
from datetime import UTC, datetime
from typing import Any

from seashield.common import signing
from seashield.common.schema import Measurements


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class VirtualBuoy:
    def __init__(self, buoy_id: str, key: bytes, seq_start: int | None = None) -> None:
        self.buoy_id = buoy_id
        self._key = key
        self._clock_seq = seq_start is None
        self._seq = _now_us() if seq_start is None else seq_start

    @property
    def next_seq(self) -> int:
        return max(self._seq, _now_us()) if self._clock_seq else self._seq

    def build_message(self, m: Measurements, observed_at: datetime | None = None) -> dict[str, Any]:
        """Return a signed message dict, ready to json.dumps and publish."""
        now = datetime.now(UTC)
        seq = self.next_seq
        msg: dict[str, Any] = {
            "buoy_id": self.buoy_id,
            "seq": seq,
            "ts": iso_utc(now),
            "observed_at": iso_utc(observed_at or now),
            "nonce": signing.new_nonce(),
            "data": m.model_dump(),
        }
        msg["sig"] = signing.sign(msg, self._key)
        self._seq = seq + 1
        return msg


def _now_us() -> int:
    """Restart-safe sequence base: microseconds since epoch.

    Each message uses max(previous + 1, now_us), so sequence numbers follow the clock.
    A restarted simulator starts at "now", above every number already sent, unless more
    than one message per microsecond was sent just before the restart (impossible in
    practice: a restart takes seconds). ~1.8e15 < 2**53, so it is exact in JavaScript too.
    """
    return time.time_ns() // 1000
