import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

NUMERIC = ["soc_pct", "battery_capacity_kwh", "soh_fraction", "speed_kmh", "load_fraction", "ambient_temp_c", "battery_temp_c", "coolant_temp_c", "thermal_power_kw", "auxiliary_power_kw", "stop_fraction", "grade_pct", "historical_consumption_kw"]
ENGINEERED = ["effective_speed_kmh", "speed_squared", "loaded_speed", "cold_severity", "hot_severity", "battery_coolant_delta", "usable_capacity_kwh"]
FEATURES = NUMERIC + ENGINEERED + ["duty_cycle"]


def engineer(frame: pd.DataFrame) -> pd.DataFrame:
    """Explicit allowlist excludes target power, future energy, mission IDs and labels."""
    x = frame.reindex(columns=NUMERIC + ["duty_cycle"]).copy()
    for col in NUMERIC:
        x[col] = pd.to_numeric(x[col], errors="coerce").replace([np.inf, -np.inf], np.nan)
    x["duty_cycle"] = x["duty_cycle"].where(x["duty_cycle"].notna(), np.nan)
    x["effective_speed_kmh"] = x.speed_kmh * (1 - x.stop_fraction)
    x["speed_squared"] = x.speed_kmh ** 2
    x["loaded_speed"] = x.effective_speed_kmh * x.load_fraction
    x["cold_severity"] = (15 - x.ambient_temp_c).clip(lower=0)
    x["hot_severity"] = (x.ambient_temp_c - 28).clip(lower=0)
    x["battery_coolant_delta"] = x.battery_temp_c - x.coolant_temp_c
    x["usable_capacity_kwh"] = x.battery_capacity_kwh * x.soh_fraction
    return x[FEATURES]


def preprocessing():
    return ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median", add_indicator=True), NUMERIC + ENGINEERED),
        ("cycle", Pipeline([("fill", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), ["duty_cycle"]),
    ])
