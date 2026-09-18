# Application-Aware Electric Vehicle Range Estimation & Digital Twin Platform

A runnable, **software-only research portfolio** aligned with the user-supplied Volvo Penta EMOB thesis brief: application-specific duty cycles, operational analytics, thermal-system effects, range and remaining-time estimation, and early digital twin concepts.

Independent demonstrator; not a Volvo product, sponsored project, or validated vehicle model. All operational records are synthetic. No hardware, CAN interfaces, BMS firmware, embedded electronics, or power electronics are required.

## Quick start

Use Python 3.11 or newer (tested with Python 3.14.4). Open a terminal **in this repository folder**.

Windows PowerShell, without needing to change activation policy:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ev_twin.train --missions 240 --windows 24 --seed 42
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

In a second PowerShell terminal, in the same folder:

```powershell
.\.venv\Scripts\python.exe -m uvicorn ev_twin.api:app --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m ev_twin.train --missions 240 --windows 24 --seed 42
python -m pytest -q
python -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
# In a second terminal, activate the same environment, then:
python -m uvicorn ev_twin.api:app --host 127.0.0.1 --port 8000
```

Dashboard: <http://127.0.0.1:8501>. Interactive API documentation: <http://127.0.0.1:8000/docs>. Stop either server with Ctrl+C. Training is explicit; opening the dashboard never silently retrains models. The dashboard and API share a Python service and SQLite file, so the dashboard also works when the API server is stopped.

## Features

- Seeded mission sequences for light load, heavy load, continuous industrial operation, and stop-and-go applications.
- SOC, nominal capacity, state of health, moving speed, load, ambient/battery/coolant temperatures, thermal and auxiliary power, stops, road grade, and strictly lagged historical consumption.
- Missing-value imputation, categorical encoding, explicit feature allowlist, and engineered temperature, speed, load, and battery features.
- Historical-mean baseline, Random Forest, and Gradient Boosting power estimators.
- MAE, RMSE, and R² for power, derived range, operating time, and planned mission energy; per-duty-cycle power results.
- Reserve-aware range, time, energy demand, shortfall, and mission feasibility.
- Controlled what-if sweeps and sequential mixed-duty mission simulation with SOC carryover and reserve termination.
- Plotly battery gauge, SOC forecasts, duty-cycle comparison, scenario curves, measured-versus-predicted scatter, and benchmark charts.
- SQLite history with UTC timestamps, complete inputs/results, model version, pagination, and dashboard export.
- Automated data, leakage, validation, energy conservation, API, persistence, simulator, and dashboard tests.

## Computed benchmark

Default generation produced **5,587 five-minute windows across 240 missions**. Whole missions were assigned to train (144 missions / 3,348 rows), validation (48 / 1,116), and test (48 / 1,123). Windows from a mission never cross partitions. Models are selected by validation power MAE; the test partition is not used for selection.

Actual held-out **power** results from the included run, seed 42:

| Estimator | MAE (kW) | RMSE (kW) | R² |
|---|---:|---:|---:|
| Historical baseline | 6.6160 | 8.7083 | 0.4620 |
| Random Forest | 2.3106 | 3.0161 | 0.9355 |
| Gradient Boosting (selected) | 2.1532 | 2.7790 | 0.9452 |

Selected model, derived outputs:

| Output | MAE | RMSE | R² |
|---|---:|---:|---:|
| Range (km) | 10.9777 | 83.6350 | 0.6981 |
| Operating time (min) | 30.4722 | 153.4906 | 0.7458 |
| 60-minute mission energy (kWh) | 2.1532 | 2.7790 | 0.9452 |

These numbers measure recovery of a synthetic generator, **not real-world accuracy**. Range/time targets extrapolate each observed power window at constant conditions; they are not measured future-trip outcomes. Low net power on downhill synthetic windows produces large extrapolated ranges and amplifies reciprocal-power errors, explaining the high range/time RMSE. Random Forest has lower derived range/time RMSE than the selected Gradient Boosting model; the selection objective is power MAE. One-hour energy metrics numerically match power metrics by unit conversion, not independent validation.

Full metrics, partitions, dependency versions, dataset hash, and per-duty-cycle results are in [artifacts/metrics.json](artifacts/metrics.json); test predictions are in [artifacts/test_predictions.csv](artifacts/test_predictions.csv). See [the model card](docs/MODEL_CARD.md) for assumptions and research limitations.

## How estimates work

The supervised target is average net battery electrical power in kW. This keeps stationary productive work meaningful, whereas kWh/km is undefined at zero speed.

```text
available_kWh = capacity_kWh × SOH × max(SOC − reserve_SOC, 0) / 100
remaining_hours = available_kWh / predicted_power_kW
effective_speed_km_h = moving_speed_km_h × (1 − stopped_fraction)
remaining_range_km = remaining_hours × effective_speed_km_h
planned_energy_kWh = predicted_power_kW × planned_minutes / 60
```

Planned energy is unconstrained demand. Deliverable energy is capped by the energy available above reserve. SOC already below reserve yields zero operating time and range. Stationary work gives zero range while retaining operating time and energy demand. Predictions use a positive 0.5 kW floor; regenerative net charging is not modeled.

Mission simulation uses prescribed, piecewise-constant conditions. It carries SOC between segments and ends at reserve; it does not dynamically solve battery thermodynamics, aging, or controller behavior. A nominal 90th-percentile validation-error band is shown only as a **heuristic sensitivity band**, not a calibrated confidence interval.

## API

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Model readiness |
| GET | `/duty-cycles` | Representative scenario defaults |
| GET | `/metrics` | Complete evaluation and provenance |
| POST | `/predict` | Predict and optionally persist (default: true) |
| POST | `/scenarios` | Compare 1–20 complete operating states with a base state |
| POST | `/simulate` | Simulate 1–48 ordered mission segments |
| GET | `/history?limit=50&offset=0` | Latest stored results, up to 500 per page |

PowerShell prediction example:

```powershell
$body = @{ state = @{ duty_cycle = 'heavy_load'; soc_pct = 80; speed_kmh = 20; load_fraction = 0.9; stop_fraction = 0.15; auxiliary_power_kw = 7 }; model = 'best'; persist = $true } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri http://127.0.0.1:8000/predict -Method Post -ContentType 'application/json' -Body $body
Invoke-RestMethod -Uri http://127.0.0.1:8000/history
```

Python example (also works in a notebook):

```python
import httpx
payload = {
    "state": {"duty_cycle": "continuous_industrial", "speed_kmh": 6,
              "load_fraction": 0.75, "stop_fraction": 0.03, "auxiliary_power_kw": 12},
    "model": "best", "persist": True,
}
response = httpx.post("http://127.0.0.1:8000/predict", json=payload)
response.raise_for_status()
print(response.json())
```

Unspecified fields use the documented `OperatingState` defaults. **A duty-cycle label alone does not apply profile defaults in the API**: callers should fetch `/duty-cycles` and merge its values into their state. This preserves independently supplied operating measurements. The dashboard automatically supplies profile defaults. Full request schemas and interactive examples are available at `/docs`.

`/scenarios` accepts `{"base": {...}, "scenarios": [{...}, {...}], "model": "best", "persist": false}`. Each scenario is a complete state with schema defaults, not a patch to the base. `/simulate` accepts `{"segments": [{"state": {...}, "duration_min": 30}], "model": "best"}`; SOC comes from the first segment and carries forward. Battery capacity, SOH, and reserve must match throughout.

## Repository structure

```text
dashboard.py             Streamlit interface and Plotly charts
ev_twin/
  config.py              Paths and duty-cycle defaults
  schemas.py             Validated operating states and API requests
  data.py                Reproducible synthetic mission generator
  features.py            Feature engineering and preprocessing
  models.py              Baseline and regression pipelines
  train.py               Mission splits, training, evaluation, artifacts
  service.py             Prediction, what-if, and mission simulation
  storage.py             SQLite persistence
  api.py                 FastAPI application factory and endpoints
tests/                   Automated regression and integration checks
docs/                    Model card, architecture, demo and CV notes
artifacts/               Model bundle, metrics, held-out predictions
data/                    Generated operational CSV and local history
requirements.txt         Exact versions used for direct dependencies
pyproject.toml           Package and Pytest configuration
```

Set `EV_TWIN_ARTIFACT_DIR` or `EV_TWIN_DB_PATH` before starting a process to override storage paths. Models are loaded on API startup; restart after retraining. The dashboard invalidates its cache when the artifact timestamp changes. Only load trusted model bundles: joblib is a pickle-based format. The local API has no authentication and should remain bound to loopback for this demonstration.

## Portfolio use

Follow [docs/DEMO_AND_PORTFOLIO.md](docs/DEMO_AND_PORTFOLIO.md) for a five-minute demonstration, CV language, and a proposed real-data thesis extension. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the component design and [docs/VALIDATION.md](docs/VALIDATION.md) for execution evidence.
