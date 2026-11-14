# Threat model

| # | Attacker capability | Stopped by crypto? | Detected by | Code / test |
|---|---|---|---|---|
| T1 | Modify message in transit | Yes | Crypto gate (HMAC) | `engine/crypto_gate.py` · `test_tampered_in_transit_rejected` |
| T2 | Fake / unregistered buoy | Yes | Crypto gate (unknown key) | `test_unknown_device_rejected` |
| T3 | Replay an old valid message | Partly | seq + timestamp window + nonce | `test_replay_rejected`, `test_stale_timestamp_rejected` |
| T4 | Compromised buoy (valid key) | **No** | Physics + AI + neighbours | `test_compromised_buoy_passes_crypto`, `test_compromised_spike_fools_baseline_but_not_seashield` |
| T5 | Slow drift | No | Temporal model / CUSUM (stretch) | TODO |
| T6 | Coordinated multi-buoy lie | No | Partially: physics + distant references | Known limitation |

**Out of scope (MVP):** link jamming / DoS, physical sensor tampering, attacks on the
monitoring centre itself.

**Core statement:** cryptography proves *who sent* the data and that it was *not changed in
transit*. It cannot prove the data is *true*. AI, physics and neighbours produce evidence,
not proof, and a human operator makes the final call on held alerts.
