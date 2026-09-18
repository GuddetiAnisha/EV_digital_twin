# Demonstration and portfolio notes

## Five-minute demonstration

1. Open the dashboard and introduce the synthetic-data scope. Explain why operating time matters for industrial machines that consume energy without traveling far.
2. Select light load and then continuous industrial operation. Compare range, operating time, power, and the energy budget. Show the battery reserve and SOC trajectory.
3. Open the what-if laboratory. Sweep load or thermal-system power. Explain that other inputs are held constant and the curves show estimator sensitivity, not causal proof.
4. Build a mixed-duty mission. Lower starting SOC to demonstrate reserve termination and mission infeasibility.
5. Save a prediction, inspect its input/output history, then show the API `/docs` page. Finish on model evidence: compare all three estimators and discuss both strong power metrics and weaker derived range/time results.

## Suggested CV entry

**Application-Aware EV Range Estimation & Digital Twin — Python, scikit-learn, FastAPI, Streamlit, Plotly, SQLite**

- Built a software-only platform for application-aware EV range, operating-time, and energy estimation across four industrial duty cycles, with thermal/load scenario analysis and reserve-aware mission simulation.
- Benchmarked historical, Random Forest, and Gradient Boosting estimators on 240 synthetic missions using mission-separated training, validation, and testing; selected Gradient Boosting achieved 2.15 kW power MAE and 0.945 R² on held-out synthetic data.
- Delivered a modular API, interactive digital twin dashboard, persistent prediction history, and automated tests covering data leakage, energy accounting, validation, simulation, and UI behavior.

Do not describe these as Volvo operational results, field-tested range accuracy, actual vehicle integration, or a completed company thesis. Explain that the next research step is validation on authorized real operational data.

## Interview discussion

- Why predict power? It supports stationary and low-speed industrial applications without dividing by zero distance.
- Why separate by mission? Random row splits would place correlated neighboring windows in train and test and inflate performance.
- Why does range RMSE remain high? Reciprocal power conversion magnifies errors when actual net power is very small; a good power score alone does not establish reliable endurance predictions.
- What is application awareness here? Duty-cycle labels plus corresponding load/speed/stop/auxiliary patterns are explicit model inputs and scenario settings. No controlled ablation claim is made.
- What makes this a twin prototype? A structured operating state drives a predictive model, future-state simulation, and an interactive representation. Physical synchronization and a validated state estimator remain future work.
- What would you study in the thesis? Machine/time-held-out validation, application-aware ablations, multi-horizon forecast targets, thermal effects, and mission-level uncertainty calibration.
