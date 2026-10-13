"""Time-based train / validation / test split. Never random (invariant 6, model card).

Each window is a block of time. A random split would let the model learn from the future,
which inflates every metric. A gap between windows keeps an attack that straddles a
boundary (a merchant-compromise campaign lasts days) from appearing on both sides.
"""

from __future__ import annotations

import numpy as np

DAY = np.timedelta64(1, "D")


def time_split(
    times: np.ndarray,
    train_share: float = 0.6,
    val_share: float = 0.2,
    gap: np.timedelta64 = DAY,
) -> dict[str, np.ndarray]:
    """Boolean masks for 'train', 'val' and 'test', by event time.

    The span between the first and last event is cut into train (train_share), a gap,
    validation (val_share), a gap, then test (whatever remains). Rows inside a gap belong
    to no set.
    """
    if train_share <= 0 or val_share <= 0 or train_share + val_share >= 1:
        raise ValueError("shares must be positive and leave room for a test window")
    times = np.asarray(times, dtype="datetime64[us]")
    start, end = times.min(), times.max()
    span = end - start
    train_end = start + span * train_share
    val_start = train_end + gap
    val_end = val_start + span * val_share
    test_start = val_end + gap
    if test_start >= end:
        raise ValueError("data spans too little time for the requested split and gaps")
    return {
        "train": times < train_end,
        "val": (times >= val_start) & (times < val_end),
        "test": times >= test_start,
    }
