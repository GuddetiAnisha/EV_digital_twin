from streamlit.testing.v1 import AppTest
from ev_twin.config import ROOT


def test_dashboard_load_and_interaction(trained, tmp_path, monkeypatch):
    import ev_twin.config as config
    monkeypatch.setattr(config, "ARTIFACT_DIR", trained[0])
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "dashboard.sqlite3")
    app = AppTest.from_file(str(ROOT / "dashboard.py"), default_timeout=60).run()
    assert not app.exception
    assert len(app.metric) == 4
    app.sidebar.selectbox[0].select("continuous_industrial").run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert any("Saved prediction" in item.value for item in app.success)
