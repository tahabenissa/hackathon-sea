"""Message signing with per-buoy HMAC-SHA256 keys.

Important: always sign and verify the *parsed JSON dict*, never a re-serialised
Pydantic model, otherwise tiny formatting differences break the signature.

Upgrade path: Ed25519 signatures (cryptography library), so that the server
only stores public keys and a database leak cannot be used to forge messages.
"""

import base64
import hashlib
import hmac
import json
import secrets
from typing import Any


def canonical_bytes(message: dict[str, Any]) -> bytes:
    """Deterministic encoding of every field except `sig`."""
    body = {k: v for k, v in message.items() if k != "sig"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sign(message: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical_bytes(message), hashlib.sha256).hexdigest()


def verify(message: dict[str, Any], key: bytes) -> bool:
    expected = sign(message, key)
    return hmac.compare_digest(expected, str(message.get("sig", "")))


def new_nonce() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(12)).decode()
