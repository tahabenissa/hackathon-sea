import json

from seashield.common import signing


def test_signed_message_verifies_after_json_roundtrip(buoy, calm, keys):
    msg = buoy.build_message(calm)
    received = json.loads(json.dumps(msg))
    assert signing.verify(received, keys["SS-B01"])


def test_any_change_breaks_signature(buoy, calm, keys):
    msg = buoy.build_message(calm)
    msg["data"]["wave_height_m"] = 9.0
    assert not signing.verify(msg, keys["SS-B01"])


def test_wrong_key_fails(buoy, calm, keys):
    msg = buoy.build_message(calm)
    assert not signing.verify(msg, keys["SS-B02"])


def test_nonces_are_unique():
    assert len({signing.new_nonce() for _ in range(1000)}) == 1000
