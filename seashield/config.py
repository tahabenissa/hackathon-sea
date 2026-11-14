"""Central settings, read from environment variables / .env (prefix SEASHIELD_)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SEASHIELD_", extra="ignore")

    env: str = "dev"

    # MQTT
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_tls: bool = False
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    topic_telemetry: str = "seashield/buoys/{buoy_id}/telemetry"
    topic_verdicts: str = "seashield/verdicts/{buoy_id}"
    topic_control_reset: str = "seashield/control/reset"  # operator only (see infra/mosquitto/acl)

    # Database
    database_url: str = "postgresql+psycopg://seashield:change-me@localhost:5432/seashield"

    # Buoys and keys
    buoys_file: str = "config/buoys.yaml"
    keys_file: str = "secrets/buoy_keys.json"

    # Security engine
    replay_window_s: int = 120
    nonce_cache_size: int = 2048

    # Simulator
    publish_interval_s: float = 2.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
