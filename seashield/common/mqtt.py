"""Helpers to build and connect a configured paho-mqtt client."""

import logging
import time

import paho.mqtt.client as mqtt

from seashield.config import Settings

log = logging.getLogger("seashield.mqtt")


def make_client(settings: Settings, client_id: str) -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    if settings.mqtt_username:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    if settings.mqtt_tls:
        client.tls_set()  # TODO Phase 9: pass the CA file of the self-signed broker cert
    return client


def connect_with_retry(client: mqtt.Client, settings: Settings, attempts: int = 30,
                       delay_s: float = 2.0) -> None:
    """The broker may start after us (docker compose): retry instead of crashing."""
    for attempt in range(1, attempts + 1):
        try:
            client.connect(settings.mqtt_host, settings.mqtt_port)
            return
        except OSError as exc:
            log.warning("MQTT %s:%s not reachable (%s), retry %d/%d",
                        settings.mqtt_host, settings.mqtt_port, exc, attempt, attempts)
            time.sleep(delay_s)
    raise ConnectionError(f"cannot reach MQTT broker {settings.mqtt_host}:{settings.mqtt_port}")
