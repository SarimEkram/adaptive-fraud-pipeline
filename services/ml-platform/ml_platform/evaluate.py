"""Metrics and threshold selection.

* PR-AUC (the headline), ROC-AUC (shown only to contrast), precision and recall
* expected cost per 1,000 transactions, using the cost matrix in docs/05
* choose the review and decline thresholds on VALIDATION, report on TEST

Cost matrix (docs/05, assumptions): a missed fraud costs its amount, a false decline costs $15,
a review costs $3 whatever the outcome (we assume the analyst gets it right), correct
approve and correct decline cost $0.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ml_platform.baseline_rules import APPROVE, DECLINE, REVIEW, rules_actions
from ml_platform.registry import DEFAULT_ROOT, latest_version_dir, read_metadata, write_metadata
from ml_platform.split import time_split
from ml_platform.train import event_times, feature_matrix, load_features

REVIEW_COST = 3.0
FALSE_DECLINE_COST = 15.0
NEVER = 1.0001  # a threshold above every score: that action never happens
MODELS = ["rules", "amount_only", "logreg", "lightgbm"]


def actions_from_scores(scores: np.ndarray, review_t: float, decline_t: float) -> np.ndarray:
    """approve below review_t, review from review_t up to decline_t, decline from decline_t."""
    actions = np.full(len(scores), APPROVE, dtype=int)
    actions[scores >= review_t] = REVIEW
    actions[scores >= decline_t] = DECLINE
    return actions


def expected_cost_from_actions(y_true, actions, amounts_cents) -> float:
    """Dollars lost per 1,000 transactions for a given set of actions."""
    y = np.asarray(y_true, dtype=bool)
    actions = np.asarray(actions)
    dollars = np.asarray(amounts_cents, dtype=float) / 100
    missed = dollars[(actions == APPROVE) & y].sum()
    reviews = (actions == REVIEW).sum() * REVIEW_COST
    false_declines = ((actions == DECLINE) & ~y).sum() * FALSE_DECLINE_COST
    return float((missed + reviews + false_declines) / len(y) * 1000)


def expected_cost(y_true, scores, amounts_cents, review_t: float, decline_t: float) -> float:
    """Expected cost per 1,000 transactions at these two thresholds."""
    actions = actions_from_scores(np.asarray(scores, dtype=float), review_t, decline_t)
    return expected_cost_from_actions(y_true, actions, amounts_cents)


def choose_thresholds(y_true, scores, amounts_cents, grid: int = 300) -> tuple[float, float, float]:
    """Pick (review_t, decline_t) that minimise expected cost. Returns thresholds and the cost.

    Sorts the scores once and keeps running totals, so the cost of any threshold pair is a
    few array lookups instead of a pass over the data. Candidate thresholds are quantiles of
    the scores, plus one above every score (meaning "never").
    """
    y = np.asarray(y_true, dtype=bool)
    s = np.asarray(scores, dtype=float)
    dollars = np.asarray(amounts_cents, dtype=float) / 100
    order = np.argsort(s, kind="stable")
    s_sorted = s[order]
    missed_if_approved = np.concatenate([[0.0], np.cumsum(np.where(y[order], dollars[order], 0.0))])
    legit_so_far = np.concatenate([[0], np.cumsum(~y[order])])

    candidates = np.unique(np.concatenate([np.quantile(s, np.linspace(0, 1, grid)), [NEVER]]))
    below = np.searchsorted(s_sorted, candidates, side="left")  # rows under each threshold

    approved_cost = missed_if_approved[below][:, None]  # rows under review_t are approved
    review_cost = REVIEW_COST * (below[None, :] - below[:, None])  # rows between the thresholds
    declined_legit = (legit_so_far[-1] - legit_so_far[below])[None, :]  # legit rows over decline_t
    cost = approved_cost + review_cost + FALSE_DECLINE_COST * declined_legit
    cost = np.where(below[None, :] >= below[:, None], cost, np.inf)  # review_t <= decline_t

    i, j = np.unravel_index(np.argmin(cost), cost.shape)
    return float(candidates[i]), float(candidates[j]), float(cost[i, j] / len(y) * 1000)


def pr_auc(y_true, scores) -> float:
    """Area under the precision-recall curve (average precision). The headline metric."""
    return float(average_precision_score(y_true, scores))


def precision_recall(y_true, flagged) -> tuple[float, float]:
    y = np.asarray(y_true, dtype=bool)
    flagged = np.asarray(flagged, dtype=bool)
    hits = (y & flagged).sum()
    precision = hits / flagged.sum() if flagged.any() else 0.0
    return float(precision), float(hits / y.sum()) if y.any() else 0.0


def attack_recall(patterns, attacks, flagged) -> dict[str, float]:
    """Per pattern: the share of attacks where at least one transaction was flagged."""
    frame = pd.DataFrame({"pattern": patterns, "attack": attacks, "flagged": flagged}).dropna(
        subset=["attack"]
    )
    caught = frame.groupby(["pattern", "attack"])["flagged"].any().groupby("pattern").mean()
    return {str(k): float(v) for k, v in caught.items()}


def pattern_pr_auc(y_true, patterns, scores) -> dict[str, float]:
    """PR-AUC of each fraud pattern against honest traffic, so an easy pattern shows up."""
    y = np.asarray(y_true, dtype=bool)
    patterns = np.asarray(patterns, dtype=object)
    out = {}
    for name in sorted({p for p in patterns[y] if p is not None}):
        keep = ~y | (patterns == name)
        out[name] = pr_auc(patterns[keep] == name, np.asarray(scores)[keep])
    return out


# Cumulative share of rows (lowest scores first) where each calibration bin ends. With about 1%
# fraud, equal-size deciles would put nine bins at "score near 0, fraud rate 0", so the bins
# get finer toward the top, where the fraud is.
CALIBRATION_EDGES = (0.0, 0.6, 0.9, 0.96, 0.98, 0.99, 0.995, 0.998, 1.0)


def calibration_bins(y_true, scores) -> dict[str, list[float]]:
    """Bins by score: mean predicted probability vs the fraud rate actually seen."""
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(scores, dtype=float)
    order = np.argsort(s, kind="stable")
    cuts = [round(edge * len(s)) for edge in CALIBRATION_EDGES]
    chunks = [order[a:b] for a, b in zip(cuts, cuts[1:], strict=False) if b > a]
    return {
        "predicted": [float(s[c].mean()) for c in chunks],
        "observed": [float(y[c].mean()) for c in chunks],
        "size": [float(len(c)) for c in chunks],
    }


def expected_calibration_error(bins: dict[str, list[float]]) -> float:
    sizes = np.array(bins["size"])
    gap = np.abs(np.array(bins["predicted"]) - np.array(bins["observed"]))
    return float((sizes * gap).sum() / sizes.sum())


def score_all(df: pd.DataFrame, version_dir: Path) -> dict[str, np.ndarray]:
    """Score every row with each saved model. Rules have no score: they give actions."""
    X = feature_matrix(df)
    booster = lgb.Booster(model_file=str(version_dir / "model.txt"))
    amount_only = joblib.load(version_dir / "amount_only.joblib")
    logreg = joblib.load(version_dir / "logreg.joblib")
    return {
        "amount_only": amount_only.predict_proba(X[["amount_cents"]])[:, 1],
        "logreg": logreg.predict_proba(X)[:, 1],
        "lightgbm": booster.predict(X),
    }


def evaluate_models(df: pd.DataFrame, masks: dict[str, np.ndarray], scores: dict[str, np.ndarray]):
    """Choose thresholds on validation, report on test. Returns (results, scores by model)."""
    y = df["is_fraud"].to_numpy(dtype=bool)
    amounts = df["amount_cents"].to_numpy()
    patterns = df["fraud_pattern"].to_numpy(dtype=object)
    attacks = df["attack_id"].to_numpy(dtype=object)
    val, test = masks["val"], masks["test"]

    rule_actions = rules_actions(df)
    scores = {"rules": rule_actions / 2.0, **scores}  # three levels: approve, review, decline

    results: dict[str, dict] = {
        "approve_all": {
            "test_cost": expected_cost_from_actions(y[test], np.zeros(test.sum()), amounts[test])
        }
    }
    for name in MODELS:
        s = scores[name]
        if name == "rules":
            thresholds = None
            actions_val, actions_test = rule_actions[val], rule_actions[test]
        else:
            review_t, decline_t, _ = choose_thresholds(y[val], s[val], amounts[val])
            thresholds = {"review": review_t, "decline": decline_t}
            actions_val = actions_from_scores(s[val], review_t, decline_t)
            actions_test = actions_from_scores(s[test], review_t, decline_t)

        flagged = actions_test >= REVIEW
        precision, recall = precision_recall(y[test], flagged)
        decline_precision, decline_recall = precision_recall(y[test], actions_test == DECLINE)
        results[name] = {
            "val_pr_auc": pr_auc(y[val], s[val]),
            "test_pr_auc": pr_auc(y[test], s[test]),
            "test_roc_auc": float(roc_auc_score(y[test], s[test])),
            "thresholds": thresholds,
            "val_cost": expected_cost_from_actions(y[val], actions_val, amounts[val]),
            "test_cost": expected_cost_from_actions(y[test], actions_test, amounts[test]),
            "precision": precision,
            "recall": recall,
            "decline_precision": decline_precision,
            "decline_recall": decline_recall,
            "reviews_per_1k": float((actions_test == REVIEW).mean() * 1000),
            "declines_per_1k": float((actions_test == DECLINE).mean() * 1000),
            "attack_recall": attack_recall(patterns[test], attacks[test], flagged),
            "pattern_pr_auc": pattern_pr_auc(y[test], patterns[test], s[test]),
        }
    bins = calibration_bins(y[test], scores["lightgbm"][test])
    results["lightgbm"]["calibration"] = {
        "brier": float(brier_score_loss(y[test], scores["lightgbm"][test])),
        "ece": expected_calibration_error(bins),
        "bins": bins,
    }
    return results, scores


def run(argv: list[str]) -> None:
    from ml_platform.report import markdown_report, plot_results

    parser = argparse.ArgumentParser(prog="mlp evaluate", description="Evaluate saved models.")
    parser.add_argument("--features", default="data/features.parquet")
    parser.add_argument("--models", default=str(DEFAULT_ROOT))
    parser.add_argument("--plot", default="docs/images/phase2-results.png")
    args = parser.parse_args(argv)

    df, _ = load_features(args.features)
    masks = time_split(event_times(df))
    version_dir = latest_version_dir(args.models)
    results, scores = evaluate_models(df, masks, score_all(df, version_dir))

    metadata = read_metadata(version_dir)
    metadata["metrics"] = {
        k: {m: v for m, v in r.items() if m != "thresholds"} for k, r in results.items()
    }
    metadata["thresholds"] = {k: r["thresholds"] for k, r in results.items() if r.get("thresholds")}
    write_metadata(version_dir, metadata)
    (version_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True))

    print(markdown_report(results, metadata))
    plot_results(df, masks, scores, results, args.plot)
    print(f"\nwrote {args.plot} and {version_dir / 'results.json'}")
