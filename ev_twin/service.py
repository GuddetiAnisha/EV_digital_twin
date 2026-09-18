from pathlib import Path
import joblib
import pandas as pd
from .features import engineer
from .schemas import OperatingState, MissionRequest, ScenarioRequest


class TwinService:
    def __init__(self, artifact_dir, store=None):
        path = Path(artifact_dir) / "models.joblib"
        if not path.exists():
            raise FileNotFoundError("Models missing. Run: python -m ev_twin.train")
        # Load only trusted, locally generated model artifacts: joblib uses pickle.
        self.bundle = joblib.load(path)
        self.store = store

    @property
    def report(self):
        return self.bundle["report"]

    def predict(self, state: OperatingState, model="best", persist=False):
        name = self.report["selected_model"] if model == "best" else model
        if name not in self.bundle["models"]:
            raise ValueError(f"Unknown model: {model}")
        power = max(0.5, float(self.bundle["models"][name].predict(engineer(pd.DataFrame([state.model_dump()])))[0]))
        available = state.battery_capacity_kwh * state.soh_fraction * max(state.soc_pct - state.reserve_soc_pct, 0) / 100
        minutes = available / power * 60
        effective_speed = state.speed_kmh * (1 - state.stop_fraction)
        expected_energy = power * state.mission_duration_min / 60
        error = self.report["validation_absolute_error_p90_kw"][name]
        low_power, high_power = max(0.5, power - error), power + error
        warnings = ["Synthetic-data research estimate; not validated on real vehicles."]
        if state.soc_pct <= state.reserve_soc_pct:
            warnings.append("SOC is at or below reserve; no usable mission energy remains.")
        if state.speed_kmh == 0:
            warnings.append("Stationary operation: range is zero; operating time remains meaningful.")
        if state.speed_kmh > 50 or state.ambient_temp_c < -20 or state.ambient_temp_c > 40 or state.grade_pct < -6 or state.grade_pct > 8:
            warnings.append("Input is outside typical synthetic training conditions; extrapolation is unreliable.")
        result = {"model": name, "model_version": self.bundle["model_version"], "input": state.model_dump(),
            "predicted_power_kw": power, "available_energy_kwh": available, "remaining_range_km": minutes / 60 * effective_speed,
            "remaining_operating_time_min": minutes, "expected_energy_consumption_kwh": expected_energy,
            "energy_deliverable_before_reserve_kwh": min(available, expected_energy), "mission_feasible": expected_energy <= available,
            "energy_shortfall_kwh": max(expected_energy - available, 0), "consumption_kwh_per_km": power / effective_speed if effective_speed > 0 else None,
            "range_sensitivity_km": [available / high_power * effective_speed, available / low_power * effective_speed],
            "time_sensitivity_min": [available / high_power * 60, available / low_power * 60],
            "sensitivity_note": "Heuristic band using validation 90th-percentile absolute power error; not a calibrated confidence interval.", "warnings": warnings}
        if persist and self.store:
            result["history_id"] = self.store.save("prediction", result)
        return result

    def scenarios(self, request: ScenarioRequest):
        base = self.predict(request.base, request.model)
        alternatives = []
        for state in request.scenarios:
            result = self.predict(state, request.model)
            result["range_delta_km"] = result["remaining_range_km"] - base["remaining_range_km"]
            result["operating_time_delta_min"] = result["remaining_operating_time_min"] - base["remaining_operating_time_min"]
            alternatives.append(result)
        output = {"base": base, "scenarios": alternatives}
        if request.persist and self.store:
            output["history_id"] = self.store.save("scenario", output)
        return output

    def simulate_mission(self, request: MissionRequest):
        """Piecewise-constant duty segments; battery SOC carries across all segments."""
        initial = request.segments[0].state
        soc = initial.soc_pct
        elapsed, distance, energy = 0., 0., 0.
        trajectory = [{"elapsed_min": 0., "soc_pct": soc, "distance_km": 0., "energy_kwh": 0.}]
        complete = True
        for segment in request.segments:
            state = OperatingState.model_validate({**segment.state.model_dump(), "soc_pct": soc, "mission_duration_min": segment.duration_min})
            prediction = self.predict(state, request.model)
            actual_minutes = min(segment.duration_min, prediction["remaining_operating_time_min"])
            consumed = prediction["predicted_power_kw"] * actual_minutes / 60
            soc = max(min(soc, state.reserve_soc_pct), soc - 100 * consumed / (state.battery_capacity_kwh * state.soh_fraction))
            elapsed += actual_minutes
            energy += consumed
            distance += state.speed_kmh * (1 - state.stop_fraction) * actual_minutes / 60
            trajectory.append({"elapsed_min": elapsed, "soc_pct": soc, "distance_km": distance, "energy_kwh": energy, "duty_cycle": state.duty_cycle, "power_kw": prediction["predicted_power_kw"]})
            if actual_minutes + 1e-9 < segment.duration_min:
                complete = False
                break
        return {"completed": complete, "trajectory": trajectory, "elapsed_min": elapsed, "distance_km": distance, "energy_consumed_kwh": energy,
            "assumption": "Conditions and power held constant within each segment; thermal inputs are prescribed, not dynamically solved."}
