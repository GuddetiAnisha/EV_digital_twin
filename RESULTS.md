# EV Digital Twin — Verified Results

## Local validation status

The project was validated locally after installing the declared dependencies and training the model artifacts.

- **21/21 automated tests passed**.
- Local Pytest result: `21 passed, 2 warnings in 5.63s`.
- The two warnings were deprecation warnings from the FastAPI/Starlette test stack and did not fail the suite.
- Model training completed successfully before dashboard launch.
- The Streamlit digital-twin dashboard loaded successfully with the trained model bundle.

## Held-out benchmark

The included benchmark uses whole-mission train/validation/test partitions so windows from the same mission do not cross splits. Model selection is based on validation power MAE; the held-out test split is not used for model selection.

| Estimator | Power MAE (kW) | Power RMSE (kW) | R² |
|---|---:|---:|---:|
| Historical baseline | 6.6160 | 8.7083 | 0.4620 |
| Random Forest | 2.3106 | 3.0161 | 0.9355 |
| **Gradient Boosting (selected)** | **2.1532** | **2.7790** | **0.9452** |

The selected Gradient Boosting estimator clearly outperformed the historical baseline on held-out synthetic power prediction.

## Verified dashboard workflow

After training, the application loaded the selected Gradient Boosting model and produced a complete live digital-twin view including:

- remaining range
- operating time
- mission energy demand
- battery power
- battery state of charge
- SOC forecast
- mission feasibility message
- application/duty-cycle controls
- model evidence and prediction history tabs

A representative validated scenario displayed:

- Remaining range: **150.5 km**
- Operating time: **307 min**
- Mission energy demand: **38.7 kWh**
- Battery power: **19.3 kW**
- State of charge: **75%**
- Selected estimator: **Gradient Boosting**
- Mission status: **planned mission fits within the estimated energy budget**

## Reproduce

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m ev_twin.train
python -m pytest -q
python -m streamlit run dashboard.py
```

Optional API:

```powershell
python -m uvicorn ev_twin.api:app --reload
```

## Interpretation

These results validate the software implementation and synthetic benchmark. They do **not** establish real-vehicle accuracy or production readiness. The project is a software-only research demonstrator using synthetic operational data, and the displayed range/time values are derived model outputs under configured operating conditions rather than measured vehicle outcomes.
