"""Feature logic. Pure functions, no I/O. Shared by online and offline (ADR-0006).

THE ORDERING RULE
    features = compute_features(txn, state)   # 1. sees only the past
    state    = update_state(txn, state)       # 2. then absorb this txn
Reversing these leaks the transaction into its own features.

Conventions (see docs/04-feature-catalog.md and docs/design-notes/phase-2-offline-model.md):
  * windows are [event_time - W, event_time): an event exactly W ago counts, one at the same
    instant or later does not
  * -1 means "unknown" for distance, time and speed on a card with no history
  * neither function changes its inputs
"""

from __future__ import annotations

import math
from bisect import insort
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from fraudcore.features.geo import haversine_km
from fraudcore.features.state import MAX_KNOWN_ITEMS, MAX_WINDOW_MS, CardState
from fraudcore.schemas import Channel, Transaction

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
ELEVATED_RISK_MCCS = {"5732", "5944", "5947"}  # electronics, jewellery, gift shops
SMALL_TXN_CENTS = 200

_MINUTE_MS = 60 * 1000
_HOUR_MS = 60 * _MINUTE_MS
_DAY_MS = MAX_WINDOW_MS

UNKNOWN = -1.0  # distance, time or speed with no previous transaction
_MIN_ZSCORE_HISTORY = 3  # fewer prior amounts than this: not enough to call anything unusual
_MIN_STD_CENTS = 100.0  # $1 floor, so identical past amounts do not give infinite z-scores
_MIN_ELAPSED_S = 60.0  # floor on elapsed time for speed, so nearby purchases seconds apart
#                        do not look like jet travel

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)


def _utc(when: datetime) -> datetime:
    return when if when.tzinfo is not None else when.replace(tzinfo=UTC)


def to_ms(when: datetime) -> int:
    """Milliseconds since 1970 (UTC), exact: integer arithmetic, no float rounding."""
    return (_utc(when) - _EPOCH) // _MILLISECOND


def _window(recent: list[tuple[int, int]], now_ms: int, width_ms: int) -> list[tuple[int, int]]:
    """Events in [now - width, now): strictly before now, at most `width` old."""
    return [(t, amount) for t, amount in recent if now_ms - width_ms <= t < now_ms]


def _local_hour(txn: Transaction) -> int:
    """Hour of day on the local mean solar clock: UTC hour shifted by longitude / 15."""
    return (_utc(txn.event_time).astimezone(UTC).hour + round(txn.lon / 15)) % 24


def compute_features(txn: Transaction, state: CardState) -> dict[str, float]:
    """Return one value per name in FEATURE_NAMES, using only state built from earlier events.

    Every value is a float. A card with empty state gets defined values (see module docs).
    """
    now = to_ms(txn.event_time)
    last_minute = _window(state.recent, now, _MINUTE_MS)
    last_10_min = _window(state.recent, now, 10 * _MINUTE_MS)
    last_hour = _window(state.recent, now, _HOUR_MS)
    last_day = _window(state.recent, now, _DAY_MS)

    if state.amt_count >= _MIN_ZSCORE_HISTORY:
        std = max(math.sqrt(state.amt_m2 / (state.amt_count - 1)), _MIN_STD_CENTS)
        zscore = (txn.amount_cents - state.amt_mean) / std
    else:
        zscore = 0.0

    if state.last_ts_ms is None or state.last_lat is None or state.last_lon is None:
        secs_since = km = speed = UNKNOWN
    else:
        secs_since = max(0.0, (now - state.last_ts_ms) / 1000)  # late events count as 0
        km = haversine_km(state.last_lat, state.last_lon, txn.lat, txn.lon)
        speed = km / (max(secs_since, _MIN_ELAPSED_S) / 3600)

    if txn.mcc in HIGH_RISK_MCCS:
        risk_bucket = 2.0
    elif txn.mcc in ELEVATED_RISK_MCCS:
        risk_bucket = 1.0
    else:
        risk_bucket = 0.0

    return {
        "amount_cents": float(txn.amount_cents),
        "txn_count_1m": float(len(last_minute)),
        "txn_count_1h": float(len(last_hour)),
        "txn_count_24h": float(len(last_day)),
        "amount_sum_1h_cents": float(sum(amount for _, amount in last_hour)),
        "small_txn_count_10m": float(
            sum(1 for _, amount in last_10_min if amount < SMALL_TXN_CENTS)
        ),
        "amount_zscore": zscore,
        "secs_since_last_txn": secs_since,
        "km_from_last_txn": km,
        "implied_speed_kmh": speed,
        "is_foreign": float(
            state.home_country is not None and txn.merchant_country != state.home_country
        ),
        "is_new_device": float(
            txn.device_id is not None and txn.device_id not in state.known_devices
        ),
        "is_new_merchant": float(txn.merchant_id not in state.known_merchants),
        "mcc_risk_bucket": risk_bucket,
        "hour_of_day": float(_local_hour(txn)),
        "is_ecommerce": float(txn.channel == Channel.ECOMMERCE),
    }


def _touch(items: list[str], value: str) -> list[str]:
    """Move `value` to the most-recent end, then drop the oldest beyond the cap (LRU)."""
    return ([v for v in items if v != value] + [value])[-MAX_KNOWN_ITEMS:]


def update_state(txn: Transaction, state: CardState) -> CardState:
    """Absorb txn into state and return the new state. The old state is left untouched."""
    ts = to_ms(txn.event_time)

    recent = list(state.recent)
    insort(recent, (ts, txn.amount_cents))  # keeps oldest-first even for late events
    newest = ts if state.last_ts_ms is None else max(ts, state.last_ts_ms)
    recent = [event for event in recent if event[0] >= newest - MAX_WINDOW_MS]

    count = state.amt_count + 1  # Welford's running mean and sum of squared differences
    delta = txn.amount_cents - state.amt_mean
    mean = state.amt_mean + delta / count
    m2 = state.amt_m2 + delta * (txn.amount_cents - mean)

    is_newest = state.last_ts_ms is None or ts >= state.last_ts_ms  # F8: never move backwards
    last = (
        (ts, txn.lat, txn.lon) if is_newest else (state.last_ts_ms, state.last_lat, state.last_lon)
    )

    devices = (
        state.known_devices if txn.device_id is None else _touch(state.known_devices, txn.device_id)
    )
    return replace(
        state,
        home_country=state.home_country or txn.merchant_country,
        recent=recent,
        last_ts_ms=last[0],
        last_lat=last[1],
        last_lon=last[2],
        known_devices=list(devices),
        known_merchants=_touch(state.known_merchants, txn.merchant_id),
        amt_count=count,
        amt_mean=mean,
        amt_m2=m2,
    )
