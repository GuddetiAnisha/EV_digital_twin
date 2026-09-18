import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from .features import preprocessing


class HistoricalBaseline(RegressorMixin, BaseEstimator):
    """Persistence benchmark: the past rolling mean predicts the next window."""
    def fit(self, x, y=None):
        return self

    def predict(self, x):
        return np.maximum(0.5, x["historical_consumption_kw"].fillna(25).to_numpy())


def build_models(seed=42):
    return {
        "baseline": HistoricalBaseline(),
        "random_forest": Pipeline([("prepare", preprocessing()), ("model", RandomForestRegressor(n_estimators=160, min_samples_leaf=2, random_state=seed, n_jobs=-1))]),
        "gradient_boosting": Pipeline([("prepare", preprocessing()), ("model", GradientBoostingRegressor(n_estimators=220, max_depth=3, learning_rate=0.06, loss="huber", random_state=seed))]),
    }
