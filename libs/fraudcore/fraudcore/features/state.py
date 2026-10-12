"""Per-card state: everything needed to compute features for the NEXT transaction.

Serialized as one JSON blob in Redis online (ADR-0004), held in memory during offline replay.
Keep it bounded: prune windows, cap sets. See docs/04 rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_WINDOW_MS = 24 * 60 * 60 * 1000  # longest feature window
MAX_KNOWN_ITEMS = 50  # cap for device and merchant sets


@dataclass
class CardState:
    card_id: str
    home_country: str | None = None

    # (event_time_ms, amount_cents) within MAX_WINDOW_MS, oldest first
    recent: list[tuple[int, int]] = field(default_factory=list)

    last_ts_ms: int | None = None
    last_lat: float | None = None
    last_lon: float | None = None

    known_devices: list[str] = field(default_factory=list)  # list, not set: keeps LRU order, JSON friendly
    known_merchants: list[str] = field(default_factory=list)

    # Welford running stats for amount_zscore
    amt_count: int = 0
    amt_mean: float = 0.0
    amt_m2: float = 0.0

    def to_json(self) -> str:
        # TODO(phase 4): serialize (json.dumps of asdict is fine to start)
        raise NotImplementedError

    @classmethod
    def from_json(cls, raw: str) -> CardState:
        # TODO(phase 4)
        raise NotImplementedError
