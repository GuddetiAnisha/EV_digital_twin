"""Seeded synthetic missions. Coefficients are illustrative, not Volvo specifications."""
import numpy as np
import pandas as pd
from .config import PROFILES


def synthetic_power(state: dict) -> float:
    """Simplified net battery power: traction + productive load + auxiliaries + thermal."""
    speed, load, stops = state["speed_kmh"], state["load_fraction"], state["stop_fraction"]
    moving = speed * (1 - stops)
    traction = (0.25 + 0.48 * load + 0.00011 * speed ** 2) * moving
    grade = state["grade_pct"] * (0.12 + 0.22 * load) * moving
    stop_loss = 0.12 * stops * speed * (0.5 + load)
    work = {"light_load": 2, "heavy_load": 14, "continuous_industrial": 23, "stop_and_go": 5}[state["duty_cycle"]] * load
    temp_penalty = 1 + 0.006 * max(15 - state["ambient_temp_c"], 0) + 0.004 * max(state["battery_temp_c"] - 35, 0)
    return max(0.8, (traction + grade + stop_loss + work) * temp_penalty + state["auxiliary_power_kw"] + state["thermal_power_kw"])


def generate_data(n_missions: int = 240, windows: int = 24, seed: int = 42) -> pd.DataFrame:
    if n_missions < 12 or windows < 2:
        raise ValueError("Use at least 12 missions and 2 windows per mission")
    rng = np.random.default_rng(seed)
    rows = []
    for mission in range(n_missions):
        cycle = list(PROFILES)[mission % 4]
        profile = PROFILES[cycle]
        capacity = float(rng.choice([80, 120, 160, 220, 300]))
        soh, soc = rng.uniform(0.82, 1), rng.uniform(65, 100)
        ambient = rng.uniform(-20, 40)
        battery_temp = np.clip(ambient + rng.uniform(4, 14), -15, 50)
        bias = rng.lognormal(0, 0.06)  # unobserved mission-specific efficiency
        past = []
        for step in range(windows):
            thermal = np.clip(0.6 + max(15 - ambient, 0) * 0.15 + max(battery_temp - 32, 0) * 0.18 + rng.normal(0, 0.3), 0, 15)
            state = dict(soc_pct=float(soc), reserve_soc_pct=10., battery_capacity_kwh=capacity,
                soh_fraction=float(soh), speed_kmh=float(np.clip(profile["speed_kmh"] + rng.normal(0, 5), 0, 75)),
                load_fraction=float(np.clip(profile["load_fraction"] + rng.normal(0, 0.09), 0, 1)),
                ambient_temp_c=float(ambient), battery_temp_c=float(battery_temp),
                coolant_temp_c=float(np.clip(battery_temp - rng.uniform(1, 6), -20, 60)), thermal_power_kw=float(thermal),
                auxiliary_power_kw=float(np.clip(profile["auxiliary_power_kw"] + rng.normal(0, 0.5), 0, 25)),
                stop_fraction=float(np.clip(profile["stop_fraction"] + rng.normal(0, 0.04), 0, 0.9)),
                grade_pct=float(np.clip(rng.normal(0, 1.5), -6, 8)), duty_cycle=cycle, mission_duration_min=60.)
            # First-window history is an independent prior; subsequent history is strictly lagged.
            history = np.mean(past[-6:]) if past else rng.uniform(15, 40)
            power = max(0.5, synthetic_power(state) * bias + rng.normal(0, 1.0))
            state.update(historical_consumption_kw=float(history), mission_id=f"M{mission:04d}",
                timestamp=(pd.Timestamp("2025-01-01", tz="UTC") + pd.Timedelta(days=mission, minutes=step * 5)).isoformat(),
                window_index=step, measured_power_kw=float(power), energy_consumed_kwh=float(power / 12))
            rows.append(state)
            past.append(power)
            soc = max(0, soc - (power / 12) / (capacity * soh) * 100)
            battery_temp = np.clip(battery_temp + 0.012 * power - 0.05 * (battery_temp - ambient) - 0.06 * thermal, -20, 60)
            if soc <= 10:
                break
    return pd.DataFrame(rows)
