import pytest

from seashield.common.schema import Measurements
from seashield.simulator.buoy import VirtualBuoy

KEYS = {"SS-B01": b"k" * 32, "SS-B02": b"q" * 32}


@pytest.fixture
def keys() -> dict[str, bytes]:
    return dict(KEYS)


@pytest.fixture
def buoy() -> VirtualBuoy:
    return VirtualBuoy("SS-B01", KEYS["SS-B01"])


@pytest.fixture
def calm() -> Measurements:
    return Measurements(wave_height_m=1.5, dominant_period_s=8.0, wind_speed_ms=6.0,
                        wind_dir_deg=220, pressure_hpa=1015.0, water_temp_c=18.0)
