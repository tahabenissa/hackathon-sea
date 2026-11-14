"""Feature engineering shared by training, evaluation and the live engine (Phase 5).

Keep ONE implementation here so offline and live features are identical.
"""

FEATURES = [
    # raw values
    "wave_height_m", "dominant_period_s", "wind_speed_ms", "pressure_hpa", "water_temp_c",
    # temporal (per buoy)
    "d_wave_height_m", "d_wind_speed_ms", "d_pressure_hpa",
    "roll_mean_wave_6", "roll_std_wave_6",
    # cross-variable
    "wave_per_wind",
    # seasonality
    "hour_sin", "hour_cos", "doy_sin", "doy_cos",
]


def build_features(df):
    """df: cleaned per-station DataFrame (UTC index) -> DataFrame[FEATURES]."""
    # TODO Phase 5
    raise NotImplementedError
