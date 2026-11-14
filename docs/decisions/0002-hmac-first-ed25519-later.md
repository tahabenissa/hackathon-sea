# 0002: HMAC-SHA256 per buoy first, Ed25519 later

**Status:** accepted · 2026-11-14

**Context:** messages need integrity and origin authentication. Buoys are constrained devices.

**Decision:** MVP uses HMAC-SHA256 with one random 256-bit key per buoy
(`infra/scripts/gen_buoy_keys.py`). The signature covers the canonical JSON of every field
except `sig`, and is verified on the raw parsed dict.

**Consequences:** simple and fast. Weakness: the server holds every secret key, so a server
breach would allow forging. Upgrade: Ed25519 signatures (server keeps public keys only),
already supported by the `cryptography` dependency.
