"""Train the amount-only sanity baseline, logistic regression and LightGBM on a TIME-BASED split.

The rules baseline needs no training. Writes a version folder (see registry.py).
Only the columns in FEATURE_NAMES ever reach a model: identifiers and ground truth stay out.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from fraudcore.features import FEATURE_NAMES
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from ml_platform.registry import DEFAULT_ROOT, new_version_dir, write_metadata
from ml_platform.split import time_split

SEED = 42
LGBM_PARAMS = {
    "objective": "binary",
    "n_estimators": 600,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 20,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "random_state": SEED,
    "deterministic": True,
    "force_row_wise": True,
    "verbose": -1,
}


def load_features(path: str | Path) -> tuple[pd.DataFrame, dict[str, str]]:
    """The replayed feature table, in event-time order, plus the file's metadata."""
    table = pq.read_table(path)
    meta = {k.decode(): v.decode() for k, v in (table.schema.metadata or {}).items()}
    return table.to_pandas(), meta


def event_times(df: pd.DataFrame) -> np.ndarray:
    """Event times as plain UTC datetime64, ready for the time split."""
    return (
        df["event_time"].dt.tz_convert("UTC").dt.tz_localize(None).to_numpy(dtype="datetime64[us]")
    )


def feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Exactly the model's input columns, in training order. Nothing else may be a feature."""
    return df[FEATURE_NAMES]


def signed_log1p(x: np.ndarray) -> np.ndarray:
    """Squash heavy tails (amounts, speeds) while keeping the sign, for the linear model."""
    return np.sign(x) * np.log1p(np.abs(x))


def fit_models(df: pd.DataFrame, masks: dict[str, np.ndarray]) -> dict[str, object]:
    """Fit on the train window; the validation window is used only to stop LightGBM early."""
    X, y = feature_matrix(df), df["is_fraud"].to_numpy(dtype=bool)
    train, val = masks["train"], masks["val"]

    amount_only = DecisionTreeClassifier(max_depth=4, min_samples_leaf=100, random_state=SEED)
    amount_only.fit(X.loc[train, ["amount_cents"]], y[train])

    logreg = Pipeline(
        [
            ("squash", FunctionTransformer(signed_log1p)),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(max_iter=2000)),
        ]
    )
    logreg.fit(X[train], y[train])

    lightgbm = lgb.LGBMClassifier(**LGBM_PARAMS)
    lightgbm.fit(
        X[train],
        y[train],
        eval_X=X[val],
        eval_y=y[val],
        eval_metric="average_precision",
        callbacks=[lgb.early_stopping(40, verbose=False)],
    )
    return {"amount_only": amount_only, "logreg": logreg, "lightgbm": lightgbm}


def save_models(models: dict[str, object], version_dir: Path) -> None:
    models["lightgbm"].booster_.save_model(str(version_dir / "model.txt"))  # type: ignore[attr-defined]
    joblib.dump(models["logreg"], version_dir / "logreg.joblib")
    joblib.dump(models["amount_only"], version_dir / "amount_only.joblib")


def describe_windows(df: pd.DataFrame, masks: dict[str, np.ndarray]) -> dict[str, dict]:
    times = event_times(df)
    y = df["is_fraud"].to_numpy(dtype=bool)
    return {
        name: {
            "start": str(times[mask].min()),
            "end": str(times[mask].max()),
            "rows": int(mask.sum()),
            "fraud_rows": int(y[mask].sum()),
        }
        for name, mask in masks.items()
    }


def run(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="mlp train", description="Train on a time-based split.")
    parser.add_argument("--features", default="data/features.parquet")
    parser.add_argument("--models", default=str(DEFAULT_ROOT))
    args = parser.parse_args(argv)

    df, source_meta = load_features(args.features)
    masks = time_split(event_times(df))
    models = fit_models(df, masks)

    version, version_dir = new_version_dir(args.models)
    save_models(models, version_dir)
    write_metadata(
        version_dir,
        {
            "version": version,
            "feature_names": FEATURE_NAMES,
            "generator_version": source_meta.get("generator_version"),
            "data": {k: source_meta.get(k) for k in ("seed", "customers", "days", "start")},
            "windows": describe_windows(df, masks),
            "lightgbm": {
                "params": LGBM_PARAMS,
                "best_iteration": int(models["lightgbm"].best_iteration_),  # type: ignore[attr-defined]
            },
            "metrics": {},  # filled in by `mlp evaluate`
            "thresholds": {},
        },
    )
    windows = describe_windows(df, masks)
    print(f"trained {version} -> {version_dir}")
    for name, w in windows.items():
        span = f"{w['start'][:10]} to {w['end'][:10]}"
        print(f"  {name:<5} {span}  {w['rows']:>8,} rows  {w['fraud_rows']:>5,} fraud")
