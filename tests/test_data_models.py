import numpy as np
import pandas as pd
import pytest
from ev_twin.data import generate_data
from ev_twin.features import engineer, FEATURES
from ev_twin.schemas import OperatingState
from ev_twin.service import TwinService


def test_generation_reproducible_and_bounded():
    a, b = generate_data(12, 5, 7), generate_data(12, 5, 7)
    pd.testing.assert_frame_equal(a, b)
    assert set(a.duty_cycle) == {"light_load", "heavy_load", "continuous_industrial", "stop_and_go"}
    assert a.measured_power_kw.gt(0).all()
    assert a.soc_pct.between(0, 100).all()
    assert np.allclose(a.energy_consumed_kwh, a.measured_power_kw / 12)


def test_history_uses_only_past_windows():
    frame = generate_data(12, 8, 9)
    for _, mission in frame.groupby("mission_id"):
        for i in range(1, len(mission)):
            expected = mission.iloc[max(0, i - 6):i].measured_power_kw.mean()
            assert mission.iloc[i].historical_consumption_kw == pytest.approx(expected)


def test_group_split_and_selection(trained):
    _, _, report = trained
    groups = [set(report["split"][s]["missions"]) for s in ["train", "validation", "test"]]
    assert not (groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])
    assert report["selected_model"] == min(report["validation_power_kw"], key=lambda name: report["validation_power_kw"][name]["mae"])
    for value in report["test"].values():
        assert all(np.isfinite(list(scores.values())).all() for scores in value.values())


def test_feature_allowlist_and_missing_values(trained):
    path, frame, _ = trained
    frame = frame.iloc[:3].copy()
    frame["future_range"] = 999999
    frame.loc[frame.index[0], "ambient_temp_c"] = np.nan
    frame.loc[frame.index[1], "load_fraction"] = np.inf
    x = engineer(frame)
    assert list(x.columns) == FEATURES
    assert "measured_power_kw" not in x and "future_range" not in x
    service = TwinService(path)
    for model in service.bundle["models"].values():
        assert np.isfinite(model.predict(x)).all()


@pytest.mark.parametrize("field,value", [("soc_pct", -1), ("speed_kmh", -1), ("load_fraction", 2), ("ambient_temp_c", float("nan")), ("thermal_power_kw", float("inf")), ("duty_cycle", "unknown")])
def test_invalid_inputs(field, value):
    with pytest.raises(ValueError):
        OperatingState(**{field: value})
