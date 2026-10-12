"""Phase 1 exit-criterion plots: does normal vs fraud spending look plausible?

Usage: python notebooks/phase1_plots.py [data/txns.parquet] [docs/images/phase1-spending.png]

Exploration only: it reads the simulator's Parquet and plots aggregates. No feature logic here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

# Validated pair (scripts/validate_palette.js): blue = normal, orange = fraud, in every panel.
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
NORMAL, FRAUD = "#2a78d6", "#eb6834"
TORONTO_UTC_OFFSET = -5  # the simulator's clock; no daylight saving

PATTERN_TITLES = {
    "stolen_card_travel": "Stolen card travel",
    "card_testing": "Card testing",
    "account_takeover": "Account takeover",
    "merchant_compromise": "Merchant compromise",
}


def _style(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, length=0, labelsize=9)


def _title(ax: plt.Axes, text: str, sub: str | None = None) -> None:
    ax.set_title(text, loc="left", color=INK, fontsize=11, fontweight="bold", pad=18 if sub else 8)
    if sub:
        ax.text(0, 1.03, sub, transform=ax.transAxes, color=INK_2, fontsize=8.5)


def main(src: str = "data/txns.parquet", out: str = "docs/images/phase1-spending.png") -> None:
    table = pq.read_table(src)
    dollars = table.column("amount_cents").to_numpy() / 100
    fraud = table.column("is_fraud").to_numpy(zero_copy_only=False).astype(bool)
    pattern = np.array(table.column("fraud_pattern").to_pylist(), dtype=object)
    times = table.column("event_time").to_numpy()
    hour_utc = (times.astype("datetime64[h]") - times.astype("datetime64[D]")).astype(int)
    hour = (hour_utc + TORONTO_UTC_OFFSET) % 24

    fig = plt.figure(figsize=(11, 7.5), facecolor=SURFACE, layout="constrained")
    grid = fig.add_gridspec(2, 4, height_ratios=[1.25, 1])
    ax_amount, ax_hour = fig.add_subplot(grid[0, :2]), fig.add_subplot(grid[0, 2:])

    # 1. Purchase size: both classes as shares of their own total, so the 1% class is visible.
    bins = np.logspace(np.log10(max(dollars.min(), 0.5)), np.log10(dollars.max()), 40)
    for mask, colour, label in ((~fraud, NORMAL, "Normal"), (fraud, FRAUD, "Fraud")):
        counts, _ = np.histogram(dollars[mask], bins=bins)
        share = counts / counts.sum()
        mid = np.sqrt(bins[:-1] * bins[1:])
        ax_amount.plot(mid, share, color=colour, linewidth=2, label=label)
        ax_amount.fill_between(mid, share, color=colour, alpha=0.12, linewidth=0)
    ax_amount.set_xscale("log")
    ax_amount.set_xticks([1, 5, 20, 100, 500], ["$1", "$5", "$20", "$100", "$500"])
    ax_amount.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax_amount.set_xlabel("Purchase size (log scale)", color=INK_2, fontsize=9)
    ax_amount.legend(frameon=False, labelcolor=INK_2, fontsize=9)
    _title(ax_amount, "Fraud sits at the extremes: tiny or large", "Share of each class, by size")
    _style(ax_amount)

    # 2. Time of day: fraud is spread across the day, so the hour alone gives little away.
    for mask, colour, label in ((~fraud, NORMAL, "Normal"), (fraud, FRAUD, "Fraud")):
        share = np.bincount(hour[mask], minlength=24) / mask.sum()
        ax_hour.plot(range(24), share, color=colour, linewidth=2, label=label)
        ax_hour.fill_between(range(24), share, color=colour, alpha=0.12, linewidth=0)
    ax_hour.set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
    ax_hour.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax_hour.set_xlabel("Hour of day (Toronto clock)", color=INK_2, fontsize=9)
    ax_hour.legend(frameon=False, labelcolor=INK_2, fontsize=9)
    _title(ax_hour, "Time of day gives little away", "Share of each class, by hour")
    _style(ax_hour)

    # 3. Fraud purchase size by pattern: small multiples, one colour (the entity is "fraud").
    for i, (name, title) in enumerate(PATTERN_TITLES.items()):
        ax = fig.add_subplot(grid[1, i])
        values = dollars[fraud & (pattern == name)]
        if len(values):
            ax.hist(values, bins=bins, color=FRAUD, alpha=0.85, linewidth=0)
            ax.axvline(np.median(values), color=INK, linewidth=1, linestyle=(0, (4, 3)))
        ax.set_xscale("log")
        ax.set_xticks([1, 10, 100], ["$1", "$10", "$100"])
        ax.set_xlim(bins[0], bins[-1])
        _title(ax, title, f"{len(values):,} transactions, median ${np.median(values):,.0f}")
        _style(ax)

    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    print(f"wrote {path}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
