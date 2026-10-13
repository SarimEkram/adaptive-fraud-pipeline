"""Feature ablation: retrain LightGBM without each feature and see what the test PR-AUC does.

The feature catalog requires this for every feature ("model with vs without it"). A feature
whose removal changes nothing is either redundant or unused; a feature whose removal collapses
the score is carrying the model. Uses the same split and settings as `mlp train`.
"""

from __future__ import annotations

import argparse

import lightgbm as lgb
import numpy as np
import pandas as pd
from fraudcore.features import FEATURE_NAMES

from ml_platform.evaluate import pr_auc
from ml_platform.split import time_split
from ml_platform.train import LGBM_PARAMS, event_times, load_features


def _fit_score(df: pd.DataFrame, masks: dict[str, np.ndarray], columns: list[str]) -> float:
    y = df["is_fraud"].to_numpy(dtype=bool)
    train, val, test = masks["train"], masks["val"], masks["test"]
    model = lgb.LGBMClassifier(**LGBM_PARAMS)
    model.fit(
        df.loc[train, columns],
        y[train],
        eval_X=df.loc[val, columns],
        eval_y=y[val],
        eval_metric="average_precision",
        callbacks=[lgb.early_stopping(40, verbose=False)],
    )
    return pr_auc(y[test], model.predict_proba(df.loc[test, columns])[:, 1])


def ablation(df: pd.DataFrame, masks: dict[str, np.ndarray]) -> dict[str, float]:
    """Test PR-AUC with all features, then with each one removed in turn."""
    scores = {"all features": _fit_score(df, masks, FEATURE_NAMES)}
    for name in FEATURE_NAMES:
        scores[f"without {name}"] = _fit_score(df, masks, [c for c in FEATURE_NAMES if c != name])
    return scores


def run(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="mlp ablate", description=__doc__.split("\n")[0])
    parser.add_argument("--features", default="data/features.parquet")
    args = parser.parse_args(argv)
    df, _ = load_features(args.features)
    scores = ablation(df, time_split(event_times(df)))
    full = scores["all features"]
    print("| Setting | Test PR-AUC | Change |\n|---|---|---|")
    for name, score in scores.items():
        change = "" if name == "all features" else f"{score - full:+.4f}"
        print(f"| {name} | {score:.4f} | {change} |")
