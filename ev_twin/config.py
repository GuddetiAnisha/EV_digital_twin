import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = Path(os.environ.get("EV_TWIN_ARTIFACT_DIR", ROOT / "artifacts"))
DB_PATH = Path(os.environ.get("EV_TWIN_DB_PATH", ROOT / "data" / "history.sqlite3"))
PROFILES = {
    "light_load": {"speed_kmh": 32.0, "load_fraction": 0.2, "stop_fraction": 0.08, "auxiliary_power_kw": 2.0},
    "heavy_load": {"speed_kmh": 20.0, "load_fraction": 0.9, "stop_fraction": 0.15, "auxiliary_power_kw": 7.0},
    "continuous_industrial": {"speed_kmh": 6.0, "load_fraction": 0.75, "stop_fraction": 0.03, "auxiliary_power_kw": 12.0},
    "stop_and_go": {"speed_kmh": 24.0, "load_fraction": 0.45, "stop_fraction": 0.5, "auxiliary_power_kw": 3.0},
}
LABELS = {k: k.replace("_", " ").title() for k in PROFILES}
