import pytest
from ev_twin.data import generate_data
from ev_twin.train import train
from ev_twin.service import TwinService
from ev_twin.storage import PredictionStore


@pytest.fixture(scope="session")
def trained(tmp_path_factory):
    path = tmp_path_factory.mktemp("models")
    frame = generate_data(n_missions=40, windows=8, seed=123)
    report = train(frame, path, seed=123)
    return path, frame, report


@pytest.fixture
def twin(trained, tmp_path):
    return TwinService(trained[0], PredictionStore(tmp_path / "test.sqlite3"))
