"""Turn evaluation results into a markdown table for the model card and a three-panel figure.

Colour follows the model in every panel: blue LightGBM, orange logistic regression, aqua
amount-only, grey rules. The palette is the validated reference palette (dataviz skill).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ml_platform.evaluate import MODELS, expected_cost  # noqa: E402

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COLOUR = {"lightgbm": "#2a78d6", "logreg": "#eb6834", "amount_only": "#1baf7a", "rules": "#8a8984"}
LABEL = {
    "rules": "Rules",
    "amount_only": "Amount only",
    "logreg": "Logistic regression",
    "lightgbm": "LightGBM",
}
PATTERNS = ["stolen_card_travel", "card_testing", "account_takeover", "merchant_compromise"]


def markdown_report(results: dict, metadata: dict) -> str:
    windows = metadata["windows"]
    lines = [
        f"## Results for {metadata['version']} (generator {metadata['generator_version']})",
        "",
        "Windows: "
        + ", ".join(
            f"{k} {w['start'][:10]} to {w['end'][:10]} ({w['fraud_rows']:,} fraud)"
            for k, w in windows.items()
        ),
        "",
        "### Test window (thresholds chosen on validation)",
        "",
        "| Model | PR-AUC | ROC-AUC | Precision | Recall | Reviews per 1k | Cost per 1k |",
        "|---|---|---|---|---|---|---|",
    ]
    for name in MODELS:
        r = results[name]
        lines.append(
            f"| {LABEL[name]} | {r['test_pr_auc']:.3f} | {r['test_roc_auc']:.3f} | "
            f"{r['precision']:.3f} | "
            f"{r['recall']:.3f} | {r['reviews_per_1k']:.1f} | ${r['test_cost']:,.2f} |"
        )
    lines += [
        "| Approve everything | n/a | n/a | n/a | 0.000 | 0.0 | "
        f"${results['approve_all']['test_cost']:,.2f} |",
        "",
        "Precision and recall count a transaction as flagged when it is reviewed or declined.",
        "",
        "### Attacks caught, by pattern (share of attacks with at least one flagged transaction)",
        "",
        "| Model | " + " | ".join(PATTERNS) + " |",
        "|---|" + "---|" * len(PATTERNS),
    ]
    for name in MODELS:
        recalls = results[name]["attack_recall"]
        lines.append(
            f"| {LABEL[name]} | "
            + " | ".join(f"{recalls.get(p, float('nan')):.2f}" for p in PATTERNS)
            + " |"
        )
    lines += [
        "",
        "### PR-AUC by pattern (each pattern against honest traffic)",
        "",
        "| Model | " + " | ".join(PATTERNS) + " |",
        "|---|" + "---|" * len(PATTERNS),
    ]
    for name in MODELS:
        pa = results[name]["pattern_pr_auc"]
        lines.append(
            f"| {LABEL[name]} | "
            + " | ".join(f"{pa.get(p, float('nan')):.3f}" for p in PATTERNS)
            + " |"
        )
    lines += [
        "",
        "### Thresholds (chosen on validation)",
        "",
        "| Model | Review | Decline |",
        "|---|---|---|",
    ]
    for name in MODELS:
        t = results[name]["thresholds"]
        if t:
            lines.append(f"| {LABEL[name]} | {t['review']:.4f} | {t['decline']:.4f} |")
    cal = results["lightgbm"]["calibration"]
    lines += [
        "",
        f"LightGBM calibration on test: Brier {cal['brier']:.5f}, "
        f"expected calibration error {cal['ece']:.5f}.",
    ]
    return "\n".join(lines)


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, length=0, labelsize=9)


def _title(ax: plt.Axes, text: str, sub: str) -> None:
    ax.set_title(text, loc="left", color=INK, fontsize=11, fontweight="bold", pad=18)
    ax.text(0, 1.03, sub, transform=ax.transAxes, color=INK_2, fontsize=8.5)


def plot_results(
    df: pd.DataFrame, masks: dict, scores: dict, results: dict, out: str | Path
) -> None:
    y = df["is_fraud"].to_numpy(dtype=bool)
    amounts = df["amount_cents"].to_numpy()
    val, test = masks["val"], masks["test"]

    fig, (ax_pr, ax_cost, ax_cal) = plt.subplots(
        1, 3, figsize=(14, 4.6), facecolor=SURFACE, layout="constrained"
    )

    # 1. Precision-recall curves on the test window.
    for name in ("amount_only", "logreg", "lightgbm"):
        precision, recall, _ = precision_recall_curve(y[test], scores[name][test])
        ax_pr.plot(
            recall,
            precision,
            color=COLOUR[name],
            linewidth=2,
            label=f"{LABEL[name]} (PR-AUC {results[name]['test_pr_auc']:.3f})",
        )
    r = results["rules"]
    ax_pr.scatter(
        [r["recall"]],
        [r["precision"]],
        color=COLOUR["rules"],
        s=60,
        zorder=3,
        label=f"Rules, one point (PR-AUC {r['test_pr_auc']:.3f})",
    )
    ax_pr.set_xlim(0, 1.02)
    ax_pr.set_ylim(0, 1.02)
    ax_pr.set_xlabel("Recall (share of fraud caught)", color=INK_2, fontsize=9)
    ax_pr.set_ylabel("Precision (share of flags that are fraud)", color=INK_2, fontsize=9)
    ax_pr.legend(
        frameon=False,
        labelcolor=INK_2,
        fontsize=8.5,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.17),
        ncol=2,
    )
    _title(ax_pr, "Precision and recall, test window", "Higher and further right is better")
    _style(ax_pr)

    # 2. Expected cost as the review threshold moves, decline threshold held at its chosen value.
    chosen = results["lightgbm"]["thresholds"]
    s_val = scores["lightgbm"][val]
    grid = np.unique(np.quantile(s_val, np.linspace(0, 1, 120)))
    grid = grid[grid <= chosen["decline"]]
    for mask, style, label in ((val, (0, (4, 3)), "Validation"), (test, "-", "Test")):
        cost = [
            expected_cost(y[mask], scores["lightgbm"][mask], amounts[mask], t, chosen["decline"])
            for t in grid
        ]
        ax_cost.plot(
            grid,
            cost,
            color=COLOUR["lightgbm"],
            linewidth=2,
            linestyle=style,
            label=f"LightGBM, {label.lower()}",
        )
    best = expected_cost(
        y[test], scores["lightgbm"][test], amounts[test], chosen["review"], chosen["decline"]
    )
    ax_cost.scatter([chosen["review"]], [best], color=COLOUR["lightgbm"], s=60, zorder=3)
    ax_cost.axhline(
        results["rules"]["test_cost"], color=COLOUR["rules"], linewidth=1.5, linestyle=(0, (2, 2))
    )
    ax_cost.text(
        grid.min(),
        results["rules"]["test_cost"],
        " Rules (test)",
        color=INK_2,
        fontsize=8.5,
        va="bottom",
    )
    ax_cost.set_xscale("log")
    ax_cost.set_xlabel(
        "Review threshold (log scale); dot = chosen on validation", color=INK_2, fontsize=9
    )
    ax_cost.set_ylabel("Expected cost per 1,000 transactions ($)", color=INK_2, fontsize=9)
    ax_cost.legend(frameon=False, labelcolor=INK_2, fontsize=8.5)
    _title(ax_cost, "Cost curve", "Lower is better; decline threshold held fixed")
    _style(ax_cost)

    # 3. Calibration: does a score of 0.1 mean about 10% fraud?
    bins = results["lightgbm"]["calibration"]["bins"]
    predicted = np.clip(bins["predicted"], 1e-4, 1)
    observed = np.clip(bins["observed"], 1e-4, 1)
    ax_cal.plot(
        [1e-4, 1],
        [1e-4, 1],
        color=COLOUR["rules"],
        linewidth=1.2,
        linestyle=(0, (4, 3)),
        label="Perfect",
    )
    ax_cal.plot(
        predicted,
        observed,
        color=COLOUR["lightgbm"],
        linewidth=2,
        marker="o",
        markersize=6,
        label="LightGBM",
    )
    ax_cal.set_xscale("log")
    ax_cal.set_yscale("log")
    ax_cal.set_xlabel("Predicted fraud probability (log)", color=INK_2, fontsize=9)
    ax_cal.set_ylabel("Observed fraud rate (log; floor 0.01%)", color=INK_2, fontsize=9)
    ax_cal.legend(frameon=False, labelcolor=INK_2, fontsize=8.5, loc="upper left")
    _title(ax_cal, "Calibration, test window", "On the dashed line, scores are real probabilities")
    _style(ax_cal)

    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
