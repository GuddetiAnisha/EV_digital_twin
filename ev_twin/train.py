import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from .config import ARTIFACT_DIR, ROOT
from .data import generate_data
from .features import engineer
from .models import build_models


def metrics(y, pred):
    return {"mae": float(mean_absolute_error(y, pred)), "rmse": float(np.sqrt(mean_squared_error(y, pred))), "r2": float(r2_score(y, pred))}


def derived(frame, power):
    available = frame.battery_capacity_kwh.to_numpy() * frame.soh_fraction.to_numpy() * np.maximum(frame.soc_pct.to_numpy() - frame.reserve_soc_pct.to_numpy(), 0) / 100
    hours = available / np.maximum(power, 0.5)
    return {"range_km": hours * frame.speed_kmh.to_numpy() * (1 - frame.stop_fraction.to_numpy()), "operating_time_min": hours * 60, "mission_energy_kwh": np.asarray(power) * frame.mission_duration_min.to_numpy() / 60}


def train(frame, out: Path = ARTIFACT_DIR, seed=42):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    train_val, test = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed).split(frame, groups=frame.mission_id))
    tr, va = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed + 1).split(frame.iloc[train_val], groups=frame.iloc[train_val].mission_id))
    train_idx, val_idx = train_val[tr], train_val[va]
    x, y = engineer(frame), frame.measured_power_kw
    models = build_models(seed)
    validation, test_metrics, residual_quantiles, per_cycle = {}, {}, {}, {}
    for name, model in models.items():
        model.fit(x.iloc[train_idx], y.iloc[train_idx])
        val_pred = np.maximum(0.5, model.predict(x.iloc[val_idx]))
        validation[name] = metrics(y.iloc[val_idx], val_pred)
        residual_quantiles[name] = float(np.quantile(np.abs(y.iloc[val_idx].to_numpy() - val_pred), 0.90))
    best = min(validation, key=lambda name: validation[name]["mae"])
    # Selection is finished before touching the test labels. Models remain fitted on train only.
    predictions = frame.iloc[test][["mission_id", "duty_cycle", "measured_power_kw"]].copy()
    for name, model in models.items():
        pred = np.maximum(0.5, model.predict(x.iloc[test]))
        predictions[name] = pred
        test_metrics[name] = {"power_kw": metrics(y.iloc[test], pred)}
        reference, estimated = derived(frame.iloc[test], y.iloc[test].to_numpy()), derived(frame.iloc[test], pred)
        test_metrics[name].update({key: metrics(reference[key], estimated[key]) for key in reference})
        per_cycle[name] = {cycle: metrics(y.iloc[test].to_numpy()[mask], pred[mask]) for cycle in sorted(frame.duty_cycle.unique()) if (mask := (frame.iloc[test].duty_cycle.to_numpy() == cycle)).sum() > 1}
    dataset_hash = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "seed": seed, "data_source": "synthetic; no Volvo data", "dataset_sha256": dataset_hash,
        "split": {label: {"rows": len(idx), "missions": sorted(frame.iloc[idx].mission_id.unique().tolist())} for label, idx in [("train", train_idx), ("validation", val_idx), ("test", test)]},
        "selected_model": best, "selection_rule": "lowest validation MAE in kW; test held out", "validation_power_kw": validation,
        "test": test_metrics, "test_by_duty_cycle_power_kw": per_cycle, "validation_absolute_error_p90_kw": residual_quantiles,
        "versions": {"python": platform.python_version(), "sklearn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__}}
    bundle = {"models": models, "report": report, "model_version": dataset_hash[:12] + "-" + sklearn.__version__}
    joblib.dump(bundle, out / "models.joblib")
    (out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    predictions.to_csv(out / "test_predictions.csv", index=False)
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic missions and benchmark three estimators")
    parser.add_argument("--missions", type=int, default=240)
    parser.add_argument("--windows", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=ARTIFACT_DIR)
    args = parser.parse_args()
    data = generate_data(args.missions, args.windows, args.seed)
    (ROOT / "data").mkdir(exist_ok=True)
    data.to_csv(ROOT / "data" / "synthetic_missions.csv", index=False)
    report = train(data, args.output, args.seed)
    print(json.dumps({"selected_model": report["selected_model"], "test": report["test"]}, indent=2))


if __name__ == "__main__":
    main()
