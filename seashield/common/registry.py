"""Load the buoy list (config/buoys.yaml) and their secret keys (secrets/buoy_keys.json)."""

import json
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Buoy:
    buoy_id: str
    name: str
    ndbc_station: str | None
    lat: float | None
    lon: float | None


def load_buoys(path: str | Path) -> list[Buoy]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [Buoy(**b) for b in raw["buoys"]]


def load_keys(path: str | Path) -> dict[str, bytes]:
    """Return {buoy_id: key_bytes}. Generate the file with infra/scripts/gen_buoy_keys.py."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {buoy_id: bytes.fromhex(hex_key) for buoy_id, hex_key in raw.items()}
