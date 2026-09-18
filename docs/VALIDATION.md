# Execution evidence

Validated locally on Windows with Python 3.14.4 and the direct dependency versions recorded in requirements.txt. All values below come from executed code, not illustrative targets.

## Training run

Command: `python -m ev_twin.train`

- Seed: 42; configured 240 missions, up to 24 windows each.
- Generated: 5,587 windows; 144 training, 48 validation, and 48 test missions.
- Selected estimator: Gradient Boosting, using validation power MAE.
- Held-out power MAE: 2.153203948493111 kW.
- Held-out power RMSE: 2.779012636256193 kW.
- Held-out power R²: 0.9452144856925683.
- The full output, including weaker range/time metrics, is preserved in artifacts/metrics.json.

## Automated tests

Command: `python -m pytest -q`

Result: **21 passed**. One upstream Starlette warning reported that its test client is deprecating httpx in favor of httpx2. This did not fail tests; httpx remains pinned to the version used in this validation run.

Coverage includes reproducible generation, strictly past-only historical features, disjoint mission splits, validation-only model selection, feature allowlisting, missing/non-finite preprocessing, invalid API input rejection, all four estimator selectors, power/energy/range unit relationships, zero usable SOC, stationary operation, mission reserve termination, sequential SOC carryover, SQLite reopening, API endpoints, absent-model behavior, and Streamlit initial load, duty-cycle change, and save interaction.

## Environment note

Initial sandboxed execution blocked Windows worker communication used by scikit-learn and temporary-directory access used by Pytest. Training and tests succeeded when run outside that sandbox. Normal local terminal execution does not require a code workaround. The servers are bound to localhost.

## Running application checks

Started Uvicorn at `127.0.0.1:8000` and Streamlit at `127.0.0.1:8501`. Actual HTTP checks returned:

- `/health`: 200, `status=ready`.
- `/predict` with baseline, Random Forest, and Gradient Boosting: all 200.
- Default-state power predictions: 28.0, 15.990327526754594, and 16.89478639199107 kW respectively.
- Streamlit `/_stcore/health`: 200.

Opened the dashboard in the browser and visually inspected the live metrics, sidebar controls, tabs, battery gauge, and SOC chart. Corrected the initial light/dark theme contrast mismatch and verified the final dark theme after restarting Streamlit.
