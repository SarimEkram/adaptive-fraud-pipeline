from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fraudcore.features import FEATURE_NAMES, CardState, compute_features, update_state
from fraudcore.features.state import MAX_KNOWN_ITEMS, MAX_WINDOW_MS
from fraudcore.schemas import Channel, Transaction

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def txn(
    at: datetime,
    amount: int = 1000,
    lat: float = 43.65,
    lon: float = -79.38,
    merchant: str = "m1",
    mcc: str = "5411",
    country: str = "CA",
    device: str | None = None,
    channel: Channel = Channel.CARD_PRESENT,
) -> Transaction:
    return Transaction(
        txn_id=uuid4(),
        card_id="c1",
        customer_id="u1",
        amount_cents=amount,
        currency="CAD",
        merchant_id=merchant,
        mcc=mcc,
        merchant_country=country,
        lat=lat,
        lon=lon,
        channel=channel,
        device_id=device,
        event_time=at,
    )


def replay(*txns: Transaction) -> CardState:
    state = CardState("c1")
    for t in txns:
        state = update_state(t, state)
    return state


# --- shape and cold start -----------------------------------------------------------------


def test_cold_start_returns_every_feature():
    f = compute_features(txn(T0), CardState("c1"))
    assert set(f) == set(FEATURE_NAMES)


def test_features_come_back_in_catalog_order_and_as_floats():
    f = compute_features(txn(T0), CardState("c1"))
    assert list(f) == FEATURE_NAMES
    assert all(isinstance(v, float) for v in f.values())


def test_cold_start_values():
    f = compute_features(txn(T0, amount=1234), CardState("c1"))
    assert f["amount_cents"] == 1234.0
    assert (f["txn_count_1m"], f["txn_count_1h"], f["txn_count_24h"]) == (0, 0, 0)
    assert f["amount_sum_1h_cents"] == 0 and f["small_txn_count_10m"] == 0
    assert f["amount_zscore"] == 0
    assert f["secs_since_last_txn"] == f["km_from_last_txn"] == f["implied_speed_kmh"] == -1
    assert f["is_foreign"] == 0  # no home country yet
    assert f["is_new_merchant"] == 1  # never seen is new
    assert f["is_new_device"] == 0  # card-present: no device at all


def test_transaction_does_not_see_itself():
    """Point-in-time: the first transaction must have zero prior velocity."""
    f = compute_features(txn(T0), CardState("c1"))
    assert f["txn_count_1m"] == 0


# --- windows: the point-in-time boundary --------------------------------------------------


def test_velocity_counts_prior_events():
    state = replay(*[txn(T0 + timedelta(seconds=i)) for i in range(3)])
    f = compute_features(txn(T0 + timedelta(seconds=10)), state)
    assert f["txn_count_1m"] == 3


@pytest.mark.parametrize(
    ("feature", "width"),
    [
        ("txn_count_1m", timedelta(minutes=1)),
        ("txn_count_1h", timedelta(hours=1)),
        ("txn_count_24h", timedelta(hours=24)),
    ],
)
def test_window_edges(feature: str, width: timedelta):
    state = replay(txn(T0))
    exactly = compute_features(txn(T0 + width), state)[feature]
    just_after = compute_features(txn(T0 + width + timedelta(milliseconds=1)), state)[feature]
    assert exactly == 1  # an event exactly one window ago still counts
    assert just_after == 0  # one millisecond older does not


def test_event_at_the_same_instant_is_not_seen():
    state = replay(txn(T0))
    assert compute_features(txn(T0), state)["txn_count_1m"] == 0


def test_event_from_the_future_is_not_seen():
    """Out-of-order delivery: state may hold a later event than the one being scored."""
    state = replay(txn(T0 + timedelta(seconds=30)))
    assert compute_features(txn(T0), state)["txn_count_1m"] == 0


def test_amount_sum_over_the_last_hour():
    state = replay(txn(T0, 500), txn(T0 + timedelta(minutes=30), 700))
    f = compute_features(txn(T0 + timedelta(minutes=61), 100), state)
    assert f["amount_sum_1h_cents"] == 700  # the first purchase is now 61 minutes old


def test_small_transaction_count_uses_a_strict_two_dollar_cut():
    state = replay(
        txn(T0, 199), txn(T0 + timedelta(seconds=1), 200), txn(T0 + timedelta(seconds=2), 50)
    )
    f = compute_features(txn(T0 + timedelta(minutes=1)), state)
    assert f["small_txn_count_10m"] == 2  # $1.99 and $0.50 count; $2.00 does not


def test_small_transaction_window_is_ten_minutes():
    state = replay(txn(T0, 100))
    assert compute_features(txn(T0 + timedelta(minutes=10)), state)["small_txn_count_10m"] == 1
    later = T0 + timedelta(minutes=10, milliseconds=1)
    assert compute_features(txn(later), state)["small_txn_count_10m"] == 0


# --- amount z-score -----------------------------------------------------------------------


def test_zscore_needs_three_prior_amounts():
    state = replay(txn(T0, 1000), txn(T0 + timedelta(minutes=1), 1200))
    assert compute_features(txn(T0 + timedelta(minutes=2), 90_000), state)["amount_zscore"] == 0


def test_zscore_flags_an_unusual_amount():
    state = replay(*[txn(T0 + timedelta(hours=i), 1000 + 100 * (i % 3)) for i in range(10)])
    normal = compute_features(txn(T0 + timedelta(days=1), 1100), state)["amount_zscore"]
    huge = compute_features(txn(T0 + timedelta(days=1), 30_000), state)["amount_zscore"]
    assert abs(normal) < 2
    assert huge > 20


def test_zscore_standard_deviation_has_a_one_dollar_floor():
    state = replay(*[txn(T0 + timedelta(hours=i), 1000) for i in range(5)])  # identical amounts
    z = compute_features(txn(T0 + timedelta(days=1), 1500), state)["amount_zscore"]
    assert z == pytest.approx(5.0)  # (1500 - 1000) / 100, not infinity


def test_welford_matches_the_textbook_mean_and_variance():
    amounts = [1000, 2000, 1500, 4000, 700]
    state = replay(*[txn(T0 + timedelta(hours=i), a) for i, a in enumerate(amounts)])
    mean = sum(amounts) / len(amounts)
    variance = sum((a - mean) ** 2 for a in amounts) / (len(amounts) - 1)
    assert state.amt_mean == pytest.approx(mean)
    assert state.amt_m2 / (state.amt_count - 1) == pytest.approx(variance)


# --- location features --------------------------------------------------------------------


def test_impossible_travel():
    state = update_state(txn(T0), CardState("c1"))  # Toronto
    f = compute_features(txn(T0 + timedelta(minutes=10), lat=51.5, lon=-0.12), state)  # London
    assert f["implied_speed_kmh"] > 1000


def test_distance_and_elapsed_time():
    state = replay(txn(T0))
    f = compute_features(txn(T0 + timedelta(hours=2), lat=51.05, lon=-114.07), state)
    assert f["secs_since_last_txn"] == 7200
    assert f["km_from_last_txn"] == pytest.approx(2700, rel=0.03)
    assert f["implied_speed_kmh"] == pytest.approx(f["km_from_last_txn"] / 2)


def test_same_place_is_zero_distance_and_zero_speed():
    state = replay(txn(T0))
    f = compute_features(txn(T0 + timedelta(minutes=5)), state)
    assert f["km_from_last_txn"] == 0 and f["implied_speed_kmh"] == 0


def test_nearby_purchases_seconds_apart_do_not_look_like_jet_travel():
    state = replay(txn(T0))
    f = compute_features(txn(T0 + timedelta(seconds=5), lat=43.659, lon=-79.38), state)  # ~1 km
    assert f["implied_speed_kmh"] < 70  # elapsed time is floored at 60 s


# --- categorical and static features ------------------------------------------------------


def test_foreign_is_judged_against_the_first_countrys_home():
    state = replay(txn(T0, country="CA"))
    assert compute_features(txn(T0 + timedelta(days=1), country="US"), state)["is_foreign"] == 1
    assert compute_features(txn(T0 + timedelta(days=1), country="CA"), state)["is_foreign"] == 0


def test_new_device_and_new_merchant():
    state = replay(txn(T0, device="phone", channel=Channel.ECOMMERCE, merchant="shop"))
    seen = compute_features(
        txn(T0 + timedelta(hours=1), device="phone", merchant="shop", channel=Channel.ECOMMERCE),
        state,
    )
    new = compute_features(
        txn(T0 + timedelta(hours=1), device="laptop", merchant="other", channel=Channel.ECOMMERCE),
        state,
    )
    assert (seen["is_new_device"], seen["is_new_merchant"]) == (0, 0)
    assert (new["is_new_device"], new["is_new_merchant"]) == (1, 1)


def test_mcc_risk_buckets():
    state = CardState("c1")
    assert compute_features(txn(T0, mcc="5411"), state)["mcc_risk_bucket"] == 0  # grocery
    assert compute_features(txn(T0, mcc="5732"), state)["mcc_risk_bucket"] == 1  # electronics
    assert compute_features(txn(T0, mcc="6051"), state)["mcc_risk_bucket"] == 2  # crypto


def test_hour_of_day_follows_longitude():
    assert compute_features(txn(T0), CardState("c1"))["hour_of_day"] == 7  # Toronto, 12:00 UTC
    van = compute_features(txn(T0, lat=49.28, lon=-123.12), CardState("c1"))
    assert van["hour_of_day"] == 4  # Vancouver, UTC-8
    late = txn(datetime(2026, 1, 1, 2, 0, tzinfo=UTC))
    assert compute_features(late, CardState("c1"))["hour_of_day"] == 21  # wraps past midnight


def test_ecommerce_flag():
    online = txn(T0, channel=Channel.ECOMMERCE, device="d")
    assert compute_features(online, CardState("c1"))["is_ecommerce"] == 1
    assert compute_features(txn(T0), CardState("c1"))["is_ecommerce"] == 0


# --- update_state: purity, order, bounds --------------------------------------------------


def test_update_and_compute_do_not_change_their_inputs():
    state = replay(txn(T0), txn(T0 + timedelta(minutes=1), device="d", channel=Channel.ECOMMERCE))
    before = (
        list(state.recent),
        list(state.known_devices),
        list(state.known_merchants),
        state.amt_count,
    )
    new = txn(T0 + timedelta(minutes=2), merchant="other", device="e", channel=Channel.ECOMMERCE)
    compute_features(new, state)
    update_state(new, state)
    after = (state.recent, state.known_devices, state.known_merchants, state.amt_count)
    assert after == before


def test_compute_then_update_is_the_ordering_rule():
    """Absorbing a transaction first would hide what makes it unusual."""
    t = txn(T0 + timedelta(minutes=5), merchant="brand_new", lat=51.05, lon=-114.07)
    state = replay(txn(T0))
    right = compute_features(t, state)
    wrong = compute_features(t, update_state(t, state))
    assert right["is_new_merchant"] == 1 and wrong["is_new_merchant"] == 0
    assert right["km_from_last_txn"] > 2000 and wrong["km_from_last_txn"] == 0
    assert right["secs_since_last_txn"] == 300 and wrong["secs_since_last_txn"] == 0


def test_a_transaction_never_counts_in_its_own_window_even_after_update():
    """The strict 'before' edge is a second line of defence for the count features."""
    t = txn(T0 + timedelta(seconds=5))
    state = update_state(t, replay(txn(T0)))
    assert compute_features(t, state)["txn_count_1m"] == 1  # only the earlier one


def test_old_events_are_pruned_and_state_stays_bounded():
    state = CardState("c1")
    for i in range(2000):  # one event a minute for about 33 hours
        state = update_state(txn(T0 + timedelta(minutes=i)), state)
    assert len(state.recent) <= 24 * 60 + 1
    assert state.recent[0][0] >= state.last_ts_ms - MAX_WINDOW_MS


def test_late_event_is_kept_in_order_and_does_not_move_last_backwards():
    state = replay(txn(T0 + timedelta(minutes=10), lat=51.05, lon=-114.07))
    state = update_state(txn(T0, lat=43.65, lon=-79.38), state)  # arrives late
    assert [t for t, _ in state.recent] == sorted(t for t, _ in state.recent)
    assert (state.last_lat, state.last_lon) == (51.05, -114.07)
    f = compute_features(txn(T0 + timedelta(minutes=11), lat=51.05, lon=-114.07), state)
    assert f["secs_since_last_txn"] == 60


def test_late_event_scores_normally_with_elapsed_time_clamped_at_zero():
    state = replay(txn(T0 + timedelta(minutes=10)))
    f = compute_features(txn(T0), state)
    assert f["secs_since_last_txn"] == 0


def test_known_sets_are_capped_and_least_recently_used_goes_first():
    state = CardState("c1")
    for i in range(MAX_KNOWN_ITEMS + 5):
        state = update_state(
            txn(
                T0 + timedelta(minutes=i),
                merchant=f"m{i}",
                device=f"d{i}",
                channel=Channel.ECOMMERCE,
            ),
            state,
        )
    assert len(state.known_merchants) == len(state.known_devices) == MAX_KNOWN_ITEMS
    assert "m0" not in state.known_merchants and f"m{MAX_KNOWN_ITEMS + 4}" in state.known_merchants
    # Using an old item again keeps it: it moves to the recent end.
    state = update_state(txn(T0 + timedelta(days=1), merchant="m10"), state)
    assert state.known_merchants[-1] == "m10"
    assert len(state.known_merchants) == MAX_KNOWN_ITEMS


def test_first_country_becomes_home_and_stays():
    state = replay(txn(T0, country="CA"), txn(T0 + timedelta(days=1), country="US"))
    assert state.home_country == "CA"
