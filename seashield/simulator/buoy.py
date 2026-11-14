"""One virtual buoy: holds its key and sequence counter, builds signed messages."""

from datetime import UTC, datetime
from typing import Any

from seashield.common import signing
from seashield.common.schema import Measurements


class VirtualBuoy:
    def __init__(self, buoy_id: str, key: bytes) -> None:
        self.buoy_id = buoy_id
        self._key = key
        self._seq = 0

    def build_message(self, m: Measurements) -> dict[str, Any]:
        """Return a signed message dict, ready to json.dumps and publish."""
        msg: dict[str, Any] = {
            "buoy_id": self.buoy_id,
            "seq": self._seq,
            "ts": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "nonce": signing.new_nonce(),
            "data": m.model_dump(),
        }
        msg["sig"] = signing.sign(msg, self._key)
        self._seq += 1
        return msg
