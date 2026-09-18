from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

DutyCycle = Literal["light_load", "heavy_load", "continuous_industrial", "stop_and_go"]
ModelName = Literal["baseline", "random_forest", "gradient_boosting", "best"]


class OperatingState(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    soc_pct: float = Field(75, ge=0, le=100)
    reserve_soc_pct: float = Field(10, ge=0, le=40)
    battery_capacity_kwh: float = Field(160, ge=20, le=400)
    soh_fraction: float = Field(0.95, ge=0.7, le=1)
    speed_kmh: float = Field(24, ge=0, le=80, description="Mean moving speed; stops excluded")
    load_fraction: float = Field(0.45, ge=0, le=1)
    ambient_temp_c: float = Field(15, ge=-25, le=45)
    battery_temp_c: float = Field(24, ge=-20, le=60)
    coolant_temp_c: float = Field(22, ge=-20, le=60)
    thermal_power_kw: float = Field(2, ge=0, le=15)
    auxiliary_power_kw: float = Field(3, ge=0, le=25)
    stop_fraction: float = Field(0.5, ge=0, le=0.95)
    grade_pct: float = Field(0, ge=-8, le=12)
    historical_consumption_kw: float = Field(28, ge=0.1, le=250, description="Lagged mean electrical power from past windows only")
    duty_cycle: DutyCycle = "stop_and_go"
    mission_duration_min: float = Field(60, gt=0, le=1440)


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: OperatingState = Field(default_factory=OperatingState)
    model: ModelName = "best"
    persist: bool = True


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base: OperatingState = Field(default_factory=OperatingState)
    scenarios: list[OperatingState] = Field(min_length=1, max_length=20)
    model: ModelName = "best"
    persist: bool = False


class MissionSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: OperatingState
    duration_min: float = Field(gt=0, le=1440, allow_inf_nan=False)


class MissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segments: list[MissionSegment] = Field(min_length=1, max_length=48)
    model: ModelName = "best"

    @model_validator(mode="after")
    def same_battery(self):
        first = self.segments[0].state
        for segment in self.segments[1:]:
            state = segment.state
            if (state.battery_capacity_kwh, state.soh_fraction, state.reserve_soc_pct) != (first.battery_capacity_kwh, first.soh_fraction, first.reserve_soc_pct):
                raise ValueError("All segments must use the same battery, SOH, and reserve")
        return self
