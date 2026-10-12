"""Feature logic. Pure functions, no I/O. Shared by online and offline (ADR-0006).

THE ORDERING RULE
    features = compute_features(txn, state)   # 1. sees only the past
    state    = update_state(txn, state)       # 2. then absorb this txn
Reversing these leaks the transaction into its own features.
"""

from __future__ import annotations

from fraudcore.features.state import CardState
from fraudcore.schemas import Transaction

# Order matters: the model is trained on this exact column order. Keep in sync with docs/04.
FEATURE_NAMES: list[str] = [
    "amount_cents",
    "txn_count_1m",
    "txn_count_1h",
    "txn_count_24h",
    "amount_sum_1h_cents",
    "small_txn_count_10m",
    "amount_zscore",
    "secs_since_last_txn",
    "km_from_last_txn",
    "implied_speed_kmh",
    "is_foreign",
    "is_new_device",
    "is_new_merchant",
    "mcc_risk_bucket",
    "hour_of_day",
    "is_ecommerce",
]

HIGH_RISK_MCCS = {"5815", "5816", "6051", "4829", "7995"}  # digital goods, crypto, wire, gambling
SMALL_TXN_CENTS = 200


def compute_features(txn: Transaction, state: CardState) -> dict[str, float]:
    """Return one value per name in FEATURE_NAMES, using only state built from earlier events.

    TODO(phase 2): implement. Requirements:
      * every key in FEATURE_NAMES present, every value a float
      * cold start (empty state) returns defined values, e.g. -1 for "unknown distance"
      * windows are strictly before txn.event_time
    """
    raise NotImplementedError


def update_state(txn: Transaction, state: CardState) -> CardState:
    """Absorb txn into state and return the new state.

    TODO(phase 2): implement. Requirements:
      * prune `recent` older than MAX_WINDOW_MS
      * update Welford stats
      * move last_* forward only if txn is newer (out-of-order events, failure mode F8)
      * cap known_devices / known_merchants with LRU eviction
    """
    raise NotImplementedError
