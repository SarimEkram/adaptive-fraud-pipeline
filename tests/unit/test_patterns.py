import math
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from fraudcore.schemas import Channel, Transaction
from gateway_sim.customers import Customer, generate_population, location_at
from gateway_sim.merchants import PLACES, Catalog
from gateway_sim.patterns import PATTERNS, CardTesting, StolenCardTravel

CATALOG = Catalog(seed=42)
NOW = datetime(2026, 1, 10, 15, tzinfo=UTC)
RUNS = 300


def _victim() -> Customer:
    people = generate_population(30, seed=1, catalog=CATALOG)
    return next(c for c in people if location_at(c, NOW) == c.home_area)


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance over the earth (haversine); a local copy for these tests."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2
    a += math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(a))


def _attacks(name: str, runs: int = RUNS) -> list[list[Transaction]]:
    victim, rng = _victim(), np.random.default_rng(0)
    return [PATTERNS[name].generate(victim, NOW, rng, CATALOG) for _ in range(runs)]


@pytest.mark.parametrize("name", list(PATTERNS))
def test_every_pattern_is_registered_and_valid(name: str) -> None:
    attacks = _attacks(name, runs=20)
    assert PATTERNS[name].name == name
    for txns in attacks:
        assert txns
        assert all(t.event_time >= NOW for t in txns)
        assert [t.event_time for t in txns] == sorted(t.event_time for t in txns)
        assert all(t.card_id == _victim().card_id for t in txns)


@pytest.mark.parametrize("name", list(PATTERNS))
def test_same_seed_gives_same_attack(name: str) -> None:
    assert _attacks(name, runs=5) == _attacks(name, runs=5)


@pytest.mark.parametrize("name", list(PATTERNS))
def test_transaction_ids_are_unique(name: str) -> None:
    ids = [t.txn_id for txns in _attacks(name, runs=50) for t in txns]
    assert len(ids) == len(set(ids))


# --- stolen card travel -------------------------------------------------------------------


def test_travel_is_far_in_person_and_large() -> None:
    victim = _victim()
    for txns in _attacks("stolen_card_travel"):
        assert 1 <= len(txns) <= 3
        for t in txns:
            assert t.channel == Channel.CARD_PRESENT and t.device_id is None
            hard = txns[0].event_time - NOW >= timedelta(hours=3)
            low, high = (6_000, 30_000) if hard else (15_000, 60_000)
            assert low <= t.amount_cents <= high
            assert _km(victim.home_lat, victim.home_lon, t.lat, t.lon) > 300


def test_travel_has_an_easy_and_a_hard_variant() -> None:
    gaps = [txns[0].event_time - NOW for txns in _attacks("stolen_card_travel")]
    easy = [g for g in gaps if g <= timedelta(minutes=90)]
    hard = [g for g in gaps if g >= timedelta(hours=3)]
    assert len(easy) + len(hard) == len(gaps)  # nothing in between
    assert 0.2 < len(hard) / len(gaps) < 0.4
    assert all(g >= timedelta(minutes=20) for g in easy)
    assert all(g <= timedelta(hours=6) for g in hard)


def test_travel_speed_is_usually_impossible_when_easy_and_plausible_when_hard() -> None:
    victim = _victim()
    easy, hard = [], []
    for txns in _attacks("stolen_card_travel"):
        hours = (txns[0].event_time - NOW) / timedelta(hours=1)
        kmh = _km(victim.home_lat, victim.home_lon, txns[0].lat, txns[0].lon) / hours
        (easy if hours <= 1.5 else hard).append(kmh)
    assert min(easy) > 200  # even the slowest easy case is faster than driving
    assert np.median(easy) > 700  # typically faster than a plane
    assert 0.6 < np.mean(np.array(easy) > 500) < 0.8  # short hops to Ottawa or Montreal are milder
    assert np.median(hard) < 400  # the hard cases look like a believable journey


def test_travel_does_nothing_if_victim_is_away() -> None:
    victim = Customer("c", "k", "CA", 43.76, -79.41)
    away = datetime(2025, 1, 3, tzinfo=UTC)  # mid-trip to Montreal
    assert StolenCardTravel().generate(victim, away, np.random.default_rng(0), CATALOG) == []


# --- card testing -------------------------------------------------------------------------


def _probes(txns: list[Transaction]) -> list[Transaction]:
    return [t for t in txns if t.amount_cents < 1_000]


def test_card_testing_is_online_from_a_new_device_at_new_shops() -> None:
    victim = _victim()
    for txns in _attacks("card_testing", runs=100):
        for t in txns:
            assert t.channel == Channel.ECOMMERCE
            assert t.device_id is not None and t.device_id not in victim.devices
        assert all(t.merchant_id not in victim.favourite_merchants for t in _probes(txns))


def _span(probes: list[Transaction]) -> timedelta:
    return probes[-1].event_time - probes[0].event_time


def test_card_testing_easy_variant_is_a_burst_of_sub_two_dollar_charges() -> None:
    easy = [
        p for txns in _attacks("card_testing") if _span(p := _probes(txns)) <= timedelta(minutes=10)
    ]
    assert 0.6 < len(easy) / RUNS < 0.8  # about 70% are the easy variant
    for probes in easy:
        assert 5 <= len(probes) <= 15
        assert all(t.amount_cents < 200 for t in probes)


def test_card_testing_hard_variant_is_slow_and_a_little_bigger() -> None:
    hard = [
        p for txns in _attacks("card_testing") if _span(p := _probes(txns)) > timedelta(minutes=10)
    ]
    assert 0.2 < len(hard) / RUNS < 0.4
    for probes in hard:
        assert 5 <= len(probes) <= 10
        assert all(100 <= t.amount_cents <= 500 for t in probes)
        gaps = [b.event_time - a.event_time for a, b in zip(probes, probes[1:], strict=False)]
        assert all(timedelta(minutes=5) <= g <= timedelta(minutes=10) for g in gaps)


def test_card_testing_sometimes_cashes_out() -> None:
    attacks = _attacks("card_testing")
    large = [txns[-1] for txns in attacks if txns[-1].amount_cents >= 20_000]
    assert 0.4 < len(large) / RUNS < 0.6
    assert all(20_000 <= t.amount_cents <= 50_000 for t in large)


def test_card_testing_class_is_the_registered_one() -> None:
    assert isinstance(PATTERNS["card_testing"], CardTesting)


# --- account takeover ---------------------------------------------------------------------


def test_takeover_is_online_new_device_and_within_three_hours() -> None:
    victim = _victim()
    for txns in _attacks("account_takeover", runs=100):
        assert 1 <= len(txns) <= 4
        assert txns[-1].event_time - NOW <= timedelta(hours=3)
        assert len({t.device_id for t in txns}) == 1
        for t in txns:
            assert t.channel == Channel.ECOMMERCE
            assert t.device_id not in victim.devices
            assert 2_500 <= t.amount_cents <= 40_000


def test_takeover_easy_cases_are_large_and_sometimes_risky() -> None:
    risky = {m.merchant_id for m in CATALOG.online_risky}
    easy = [
        txns for txns in _attacks("account_takeover") if min(t.amount_cents for t in txns) >= 10_000
    ]
    assert 0.6 < len(easy) / RUNS < 0.8
    hit = sum(t.merchant_id in risky for txns in easy for t in txns)
    total = sum(len(txns) for txns in easy)
    assert 0.3 < hit / total < 0.5


def test_takeover_hard_cases_are_modest_and_never_risky() -> None:
    risky = {m.merchant_id for m in CATALOG.online_risky}
    hard = [
        txns for txns in _attacks("account_takeover") if max(t.amount_cents for t in txns) <= 9_000
    ]
    assert 0.2 < len(hard) / RUNS < 0.4
    assert not any(t.merchant_id in risky for txns in hard for t in txns)


def test_takeover_location_is_sometimes_local_sometimes_far() -> None:
    victim = _victim()
    near = sum(
        _km(victim.home_lat, victim.home_lon, txns[0].lat, txns[0].lon) < 1
        for txns in _attacks("account_takeover")
    )
    assert 0.35 < near / RUNS < 0.65


# --- merchant compromise ------------------------------------------------------------------


def test_compromise_is_quiet_online_and_unfamiliar() -> None:
    victim = _victim()
    for txns in _attacks("merchant_compromise", runs=100):
        assert 1 <= len(txns) <= 2
        assert txns[-1].event_time - NOW <= timedelta(hours=6)
        for t in txns:
            assert t.channel == Channel.ECOMMERCE
            assert t.device_id not in victim.devices
            assert t.merchant_id not in victim.favourite_merchants
            assert 3_000 <= t.amount_cents <= 25_000


def test_far_places_exist_for_every_pattern() -> None:
    assert {"montreal", "ottawa", "calgary", "vancouver", "new_york"} <= set(PLACES)
