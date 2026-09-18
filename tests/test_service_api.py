import pytest
from fastapi.testclient import TestClient
from ev_twin.api import create_app
from ev_twin.schemas import OperatingState, ScenarioRequest, MissionRequest, MissionSegment
from ev_twin.storage import PredictionStore


@pytest.mark.parametrize("model", ["baseline", "random_forest", "gradient_boosting", "best"])
def test_energy_accounting(twin, model):
    state = OperatingState()
    result = twin.predict(state, model)
    assert result["available_energy_kwh"] == pytest.approx(160 * .95 * .65)
    assert result["remaining_operating_time_min"] * result["predicted_power_kw"] / 60 == pytest.approx(result["available_energy_kwh"])
    assert result["remaining_range_km"] == pytest.approx(result["remaining_operating_time_min"] / 60 * 12)
    assert result["expected_energy_consumption_kwh"] == pytest.approx(result["predicted_power_kw"])


def test_reserve_stationary_and_shortfall(twin):
    empty = twin.predict(OperatingState(soc_pct=5))
    assert empty["remaining_range_km"] == 0
    assert empty["remaining_operating_time_min"] == 0
    assert not empty["mission_feasible"]
    parked = twin.predict(OperatingState(speed_kmh=0))
    assert parked["remaining_range_km"] == 0
    assert parked["remaining_operating_time_min"] > 0
    assert parked["consumption_kwh_per_km"] is None


def test_scenarios_and_persistence(twin):
    state = OperatingState()
    result = twin.scenarios(ScenarioRequest(base=state, scenarios=[state, OperatingState(soc_pct=90)], model="baseline", persist=True))
    assert result["scenarios"][0]["range_delta_km"] == 0
    assert result["scenarios"][1]["range_delta_km"] > 0
    assert twin.store.history()[0]["payload"]["base"]["input"] == state.model_dump()
    again = PredictionStore(twin.store.path)
    assert again.history()[0]["kind"] == "scenario"


def test_mission_stops_at_reserve(twin):
    state = OperatingState(soc_pct=12, historical_consumption_kw=30)
    result = twin.simulate_mission(MissionRequest(segments=[MissionSegment(state=state, duration_min=60)] * 3, model="baseline"))
    assert not result["completed"]
    assert result["trajectory"][-1]["soc_pct"] == pytest.approx(10)
    assert result["energy_consumed_kwh"] == pytest.approx(160 * .95 * .02)
    assert result["elapsed_min"] == pytest.approx(160 * .95 * .02 / 30 * 60)


def test_mission_carries_soc_without_recharge(twin):
    state = OperatingState()
    result = twin.simulate_mission(MissionRequest(segments=[MissionSegment(state=state, duration_min=10)] * 2, model="baseline"))
    assert result["completed"]
    assert result["energy_consumed_kwh"] == pytest.approx(28 / 3)
    assert result["trajectory"][-1]["soc_pct"] < result["trajectory"][1]["soc_pct"] < 75


def test_api_roundtrip_and_validation(trained, tmp_path):
    with TestClient(create_app(trained[0], tmp_path / "api.sqlite3")) as client:
        assert client.get("/health").json()["status"] == "ready"
        assert len(client.get("/duty-cycles").json()) == 4
        response = client.post("/predict", json={"state": OperatingState().model_dump()})
        assert response.status_code == 200
        assert response.json()["history_id"] == 1
        assert len(client.get("/history").json()) == 1
        assert client.get("/metrics").json()["selected_model"]
        assert client.post("/predict", json={"state": {"soc_pct": 101}}).status_code == 422
        assert client.post("/predict", json={"model": "arbitrary"}).status_code == 422
        assert client.get("/history?limit=10000").status_code == 422
        assert client.post("/scenarios", json={"scenarios": [{}]}).status_code == 200
        assert client.post("/simulate", json={"segments": [{"state": {}, "duration_min": 10}]}).status_code == 200


def test_missing_models_is_actionable(tmp_path):
    with TestClient(create_app(tmp_path, tmp_path / "db.sqlite3")) as client:
        assert client.get("/health").json()["status"] == "models_missing"
        assert client.post("/predict", json={}).status_code == 503
