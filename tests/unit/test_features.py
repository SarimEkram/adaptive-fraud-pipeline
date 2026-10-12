from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fraudcore.features import FEATURE_NAMES, CardState, compute_features, update_state
from fraudcore.schemas import Channel, Transaction

pytestmark = pytest.mark.xfail(reason="phase 2: implement features", raises=NotImplementedError)

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def txn(at: datetime, amount: int = 1000, lat: float = 43.65, lon: float = -79.38) -> Transaction:
    return Transaction(
        txn_id=uuid4(),
        card_id="c1",
        customer_id="u1",
        amount_cents=amount,
        currency="CAD",
        merchant_id="m1",
        mcc="5411",
        merchant_country="CA",
        lat=lat,
        lon=lon,
        channel=Channel.CARD_PRESENT,
        event_time=at,
    )


def test_cold_start_returns_every_feature():
    f = compute_features(txn(T0), CardState("c1"))
    assert set(f) == set(FEATURE_NAMES)


def test_transaction_does_not_see_itself():
    """Point-in-time: the first transaction must have zero prior velocity."""
    f = compute_features(txn(T0), CardState("c1"))
    assert f["txn_count_1m"] == 0


def test_velocity_counts_prior_events():
    state = CardState("c1")
    for i in range(3):
        state = update_state(txn(T0 + timedelta(seconds=i)), state)
    f = compute_features(txn(T0 + timedelta(seconds=10)), state)
    assert f["txn_count_1m"] == 3


def test_impossible_travel():
    state = update_state(txn(T0), CardState("c1"))  # Toronto
    f = compute_features(txn(T0 + timedelta(minutes=10), lat=51.5, lon=-0.12), state)  # London
    assert f["implied_speed_kmh"] > 1000
