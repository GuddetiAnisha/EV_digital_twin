# Model card and synthetic data specification

## Intended use

Research demonstration of application-aware energy estimation and early digital twin concepts. Supports comparative experiments and software architecture discussion for the Volvo Penta EMOB thesis brief supplied by the user. Not affiliated with Volvo Penta. No field deployment claims.

## Dataset

The default generator creates 240 missions, balanced by assigned application, with up to 24 five-minute windows per mission. Missions end early if SOC reaches reserve, so row counts differ across applications. Battery capacities are sampled from 80, 120, 160, 220, and 300 kWh; SOH is 0.82–1.0; initial SOC is 65–100%; ambient temperature is −20–40 °C. All coefficients and profile values are illustrative assumptions.

| Application | Moving speed (km/h) | Load | Stopped fraction | Auxiliary demand (kW) |
|---|---:|---:|---:|---:|
| Light load | 32 | 0.20 | 0.08 | 2 |
| Heavy load | 20 | 0.90 | 0.15 | 7 |
| Continuous industrial | 6 | 0.75 | 0.03 | 12 |
| Stop-and-go | 24 | 0.45 | 0.50 | 3 |

Speeds, loads, stops, and auxiliary demands vary around these defaults. A simplified power equation combines speed-dependent traction, road grade, stop losses, application-dependent productive work, cold/hot efficiency penalties, thermal demand, and auxiliary loads. Mission-level multiplicative efficiency noise and independent measurement noise prevent a perfectly deterministic target. Battery temperature is updated with a simple illustrative heat balance during generation; the prediction service does not use that update as a validated thermal solver.

Historical consumption is the mean power of at most the preceding six windows within the same mission. The first window receives an independent random prior. Future/current target values never enter this history. All input fields are assumed to be available before the forecast window, including a planned speed/load/thermal operating point. With real telemetry, those fields must be time-aligned to avoid forecasting from measurements only available after the target window.

## Preprocessing and evaluation

- Feature engineering selects an explicit input allowlist; measured power, observed window energy, mission identifiers, and timestamps are excluded.
- Non-finite numeric features become missing values. Median imputation and categorical imputation/encoding are fitted only on training rows.
- Whole missions are split 60/20/20 using a fixed seed; this prevents adjacent windows from appearing in both train and test.
- Historical baseline: previous-window rolling mean, with a 25 kW fallback for missing history.
- Random Forest: 160 trees, minimum two samples per leaf.
- Gradient Boosting: 220 stages, depth 3, learning rate 0.06, Huber loss.
- Model selection uses validation MAE on power. Test metrics are computed after selection. Models are not refitted on validation data, preserving the interpretation of the validation residual bands.
- The test is an in-distribution synthetic mission split, not a temporal or new-machine generalization study. IDs/partitions, dataset hash, versions, and seed are preserved in metrics.json.

## Output semantics and limitations

Power is average net discharge in kW. Range and time are deterministic downstream calculations using available energy above reserve. Expected energy uses requested mission duration. State of health scales usable capacity; detailed battery degradation and temperature-dependent capacity are not included.

Derived labels extrapolate a single synthetic observation indefinitely. At low observed net power, range/time become very large and errors are amplified by division. The large RMSE compared with MAE is preserved in the report rather than hidden by clipping. The default 60-minute energy target is a scaled power target, not a separately measured horizon forecast. No independently validated range or endurance claims should be made.

The sensitivity band adds/subtracts validation p90 absolute power error before converting to range/time. Correlated windows, distribution shifts, and input uncertainty mean this is not a guaranteed 90% coverage interval. Out-of-envelope warnings are a limited heuristic and do not establish that all other inputs are in-distribution. ML response surfaces need not be monotonic or causal. Extreme combinations are accepted for software testing but may be unsupported by the training data.

What-if sweeps hold all other fields fixed. A cold-weather scenario does not automatically change coolant temperature or thermal-system power. Mixed-duty simulation recomputes power at each segment start, carries SOC forward, and holds segment conditions constant. There is no state estimator, live telemetry connection, physical synchronization, or closed-loop control: this is a digital twin **prototype**, not an operational twin.

## Real-data thesis extension

1. Agree on representative machines, duty-cycle labels, sampling intervals, and mission boundaries with domain experts.
2. Replace synthetic generation with appropriately authorized, de-identified operational records and consistent units.
3. Define causal feature availability; calculate lagged consumption separately for each machine and mission. Exclude post-horizon measurements.
4. Split by machine and time, reserve a final untouched deployment-like test set, and report confidence intervals with mission-level bootstrap resampling.
5. Evaluate multi-horizon energy, actual completion range/endurance, low-SOC performance, temperature regimes, application shifts, and calibration.
6. Compare application-aware models against application-agnostic and physics/hybrid baselines using a prespecified ablation study.
7. Replace illustrative thermal behavior with measured thermal-system signals and separately validated thermal/usable-capacity models.
8. Test drift detection, safe fallback behavior, model versioning, and read-only telemetry ingestion before any operational integration.
