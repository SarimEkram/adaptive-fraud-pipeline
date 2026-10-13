"""Hand-written rules baseline: the business benchmark the model has to beat.

These are plain thresholds on features that a fraud analyst would write on day one. They are
not feature logic (that lives in fraudcore) and they were written before looking at any
results. If they are ever tuned, tune on the validation window only. Phase 3 moves the live
version of these rules into `scoring/rules.py`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

APPROVE, REVIEW, DECLINE = 0, 1, 2


def rules_actions(features: pd.DataFrame) -> np.ndarray:
    """One action per row: 0 approve, 1 review, 2 decline. A decline rule beats a review rule."""
    f = features
    review = (
        ((f["is_new_device"] == 1) & (f["amount_cents"] >= 10_000))  # new device, big spend
        | ((f["mcc_risk_bucket"] == 2) & (f["amount_cents"] >= 5_000))  # cash-like goods
        | (f["txn_count_1m"] >= 5)  # many purchases in a minute
        | ((f["amount_zscore"] > 6) & (f["amount_cents"] >= 15_000))  # far above their usual
    )
    decline = (
        ((f["implied_speed_kmh"] > 800) & (f["km_from_last_txn"] > 300))  # impossible travel
        | (f["small_txn_count_10m"] >= 4)  # a run of tiny charges: card testing
    )
    actions = np.full(len(f), APPROVE, dtype=int)
    actions[review.to_numpy()] = REVIEW
    actions[decline.to_numpy()] = DECLINE
    return actions
