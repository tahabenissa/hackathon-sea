"""Small helper to build a configured paho-mqtt client (Phase 2)."""

import paho.mqtt.client as mqtt

from seashield.config import Settings


def make_client(settings: Settings, client_id: str) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set()  # TODO Phase 9: pass the CA file of the self-signed broker cert
    return client
