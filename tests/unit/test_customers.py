from datetime import UTC, date, datetime, timedelta
from statistics import median

import numpy as np
from fraudcore.schemas import Channel, Transaction
from gateway_sim.customers import (
    Customer,
    burst_transactions,
    daily_transactions,
    generate_population,
    location_at,
    micro_burst_transactions,
    normal_transaction,
    online_location,
)
from gateway_sim.merchants import PLACES, Catalog

CATALOG = Catalog(seed=42)
DAY0 = datetime(2025, 1, 1, tzinfo=UTC)  # a default Customer departs on a trip at 11:00 UTC


def _run(n: int = 60, days: int = 14, seed: int = 1) -> list[Transaction]:
    customers = generate_population(n, seed=seed, catalog=CATALOG)
    rng = np.random.default_rng(seed)
    start = date(2026, 1, 1)
    return [
        t
        for c in customers
        for d in range(days)
        for t in daily_transactions(c, start + timedelta(days=d), rng, CATALOG)
    ]


# --- population ---------------------------------------------------------------------------


def test_population_is_reproducible() -> None:
    assert generate_population(30, seed=7, catalog=CATALOG) == generate_population(
        30, seed=7, catalog=CATALOG
    )


def test_population_ids_unique_and_domestic() -> None:
    people = generate_population(100, seed=3, catalog=CATALOG)
    assert len({c.customer_id for c in people}) == 100
    assert len({c.card_id for c in people}) == 100
    assert {c.home_country for c in people} == {"CA"}


def test_favourites_exist_in_catalog() -> None:
    for c in generate_population(30, seed=3, catalog=CATALOG):
        assert c.favourite_merchants
        assert all(m in CATALOG.by_id for m in c.favourite_merchants)


# --- trips --------------------------------------------------------------------------------


def test_trip_timeline_home_transit_away_transit_home() -> None:
    c = Customer("c", "k", "CA", 43.76, -79.41)  # period 105 d, length 4 d, first stop Montreal
    assert location_at(c, DAY0 + timedelta(hours=10, minutes=59)) == "north_york"
    assert location_at(c, DAY0 + timedelta(hours=11)) is None  # left at 06:00 Toronto time
    assert location_at(c, DAY0 + timedelta(hours=16, minutes=59)) is None
    assert location_at(c, DAY0 + timedelta(hours=17)) == "montreal"  # six hours of travel
    assert location_at(c, DAY0 + timedelta(days=4, hours=10)) == "montreal"
    assert location_at(c, DAY0 + timedelta(days=4, hours=11)) is None  # heading home
    assert location_at(c, DAY0 + timedelta(days=4, hours=17)) == "north_york"


def test_next_trip_goes_to_a_different_city() -> None:
    c = Customer("c", "k", "CA", 43.76, -79.41)
    assert location_at(c, DAY0 + timedelta(days=105, hours=20)) == "ottawa"


def test_purchases_follow_the_customer_on_a_trip() -> None:
    c = Customer("c", "k", "CA", 43.76, -79.41, favourite_merchants=[])
    rng = np.random.default_rng(0)
    montreal = PLACES["montreal"]
    now = DAY0 + timedelta(days=2)
    txns = [t for _ in range(200) if (t := normal_transaction(c, now, rng, CATALOG))]
    assert txns

    def near_montreal(t: Transaction) -> bool:
        return abs(t.lat - montreal.lat) < 0.05 and abs(t.lon - montreal.lon) < 0.05

    in_person = [t for t in txns if t.channel == Channel.CARD_PRESENT]
    online = [t for t in txns if t.channel == Channel.ECOMMERCE]
    assert in_person and all(near_montreal(t) for t in in_person)  # shops are where they are
    assert sum(near_montreal(t) for t in online) / len(online) > 0.85  # a VPN can land elsewhere


def test_no_purchases_while_in_transit() -> None:
    c = Customer("c", "k", "CA", 43.76, -79.41)
    rng = np.random.default_rng(0)
    assert normal_transaction(c, DAY0 + timedelta(hours=13), rng, CATALOG) is None


# --- single transactions ------------------------------------------------------------------


def test_channel_rules_hold() -> None:
    for t in _run(n=30, days=7):
        assert t.event_time.tzinfo is not None
        if t.channel == Channel.ECOMMERCE:
            assert t.device_id is not None
        else:
            assert t.device_id is None


def test_amounts_are_integer_cents_and_plausible() -> None:
    txns = _run()
    assert all(isinstance(t.amount_cents, int) and t.amount_cents >= 99 for t in txns)
    assert 500 <= median(t.amount_cents for t in txns) <= 2_000  # roughly $5 to $20
    big = sum(t.amount_cents >= 6_000 for t in txns) / len(txns)
    assert 0.002 < big < 0.08  # large purchases exist but are rare


def test_most_traffic_is_online_but_not_all() -> None:
    txns = _run()
    online = sum(t.channel == Channel.ECOMMERCE for t in txns) / len(txns)
    assert 0.4 < online < 0.8


def test_timing_varies_across_the_day() -> None:
    hours = {(t.event_time - timedelta(hours=5)).hour for t in _run()}
    assert len(hours) >= 20


def test_honest_customers_rarely_touch_risky_merchants() -> None:
    risky = {m.merchant_id for m in CATALOG.online_risky}
    txns = _run()
    assert sum(t.merchant_id in risky for t in txns) / len(txns) < 0.02  # in-app buys included


def test_new_phone_changes_the_device_after_upgrade_day() -> None:
    c = Customer(
        "c",
        "k",
        "CA",
        43.76,
        -79.41,
        online_share=1.0,
        devices=["old_phone", "laptop"],
        replacement_phone="new_phone",
        upgrade_day=date(2025, 1, 10),
        trip_offset_days=50,  # keep trips out of the way
    )
    rng = np.random.default_rng(0)
    before = datetime(2025, 1, 5, 15, tzinfo=UTC)
    after = datetime(2025, 1, 12, 15, tzinfo=UTC)
    seen_before = {normal_transaction(c, before, rng, CATALOG).device_id for _ in range(100)}
    seen_after = {normal_transaction(c, after, rng, CATALOG).device_id for _ in range(100)}

    def usual(devices: set[str]) -> set[str]:
        return {d for d in devices if "_b" not in d}  # drop one-off new browsers

    assert usual(seen_before) == {"old_phone", "laptop"}
    assert usual(seen_after) == {"new_phone", "laptop"}


# --- bursts and days ----------------------------------------------------------------------


def test_burst_is_small_quick_familiar_and_in_person() -> None:
    c = generate_population(1, seed=5, catalog=CATALOG)[0]
    rng = np.random.default_rng(0)
    now = datetime(2026, 1, 3, 15, tzinfo=UTC)
    burst = burst_transactions(c, now, rng, CATALOG)
    assert 2 <= len(burst) <= 4
    assert burst[-1].event_time - burst[0].event_time <= timedelta(minutes=15)
    assert all(250 <= t.amount_cents <= 700 for t in burst)
    assert all(t.channel == Channel.CARD_PRESENT for t in burst)


def test_no_burst_while_away() -> None:
    c = Customer("c", "k", "CA", 43.76, -79.41)
    assert burst_transactions(c, DAY0 + timedelta(days=2), np.random.default_rng(0), CATALOG) == []


def test_daily_transactions_are_sorted_and_reproducible() -> None:
    c = generate_population(1, seed=9, catalog=CATALOG)[0]
    day = date(2026, 2, 1)
    first = daily_transactions(c, day, np.random.default_rng(4), CATALOG)
    again = daily_transactions(c, day, np.random.default_rng(4), CATALOG)
    assert first == again
    assert [t.event_time for t in first] == sorted(t.event_time for t in first)


# --- messiness that keeps the data honest -------------------------------------------------


def test_online_location_is_mostly_true_but_sometimes_elsewhere() -> None:
    c = Customer("c", "k", "CA", 43.76, -79.41)
    rng = np.random.default_rng(0)
    spots = [online_location(c, "north_york", rng) for _ in range(3000)]
    true = sum(s == (43.76, -79.41) for s in spots) / len(spots)
    far = sum(abs(s[1] - (-79.41)) > 5 for s in spots) / len(spots)
    assert 0.85 < true < 0.95  # about 90% at the customer's real position
    assert 0.005 < far < 0.04  # a few percent land in a far city (VPN, carrier)


def test_honest_customers_sometimes_use_a_new_device() -> None:
    c = Customer("c", "k", "CA", 43.76, -79.41, online_share=1.0, trip_offset_days=50)
    rng = np.random.default_rng(0)
    at = datetime(2025, 1, 20, 15, tzinfo=UTC)
    devices = [normal_transaction(c, at, rng, CATALOG).device_id for _ in range(2000)]
    fresh = sum("_b" in d for d in devices) / len(devices)
    assert 0.015 < fresh < 0.05


def test_micro_burst_is_small_online_quick_and_one_shop() -> None:
    c = generate_population(1, seed=5, catalog=CATALOG)[0]
    rng = np.random.default_rng(1)
    now = datetime(2026, 1, 3, 15, tzinfo=UTC)
    burst = micro_burst_transactions(c, now, rng, CATALOG)
    assert 3 <= len(burst) <= 6
    assert len({t.merchant_id for t in burst}) == 1
    assert all(t.channel == Channel.ECOMMERCE and t.device_id for t in burst)
    assert all(99 <= t.amount_cents <= 499 for t in burst)
    assert burst[-1].event_time - burst[0].event_time <= timedelta(minutes=15)


def test_no_micro_burst_while_away() -> None:
    c = Customer("c", "k", "CA", 43.76, -79.41)
    assert (
        micro_burst_transactions(c, DAY0 + timedelta(days=2), np.random.default_rng(0), CATALOG)
        == []
    )
