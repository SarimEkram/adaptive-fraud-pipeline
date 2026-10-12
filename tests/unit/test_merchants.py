import re

from gateway_sim.merchants import (
    LOCAL_KINDS,
    ONLINE_KINDS,
    PLACES,
    RISKY_ONLINE_KINDS,
    Catalog,
)


def test_same_seed_builds_identical_catalog() -> None:
    assert Catalog(seed=1).by_id == Catalog(seed=1).by_id


def test_different_seed_moves_merchants() -> None:
    assert Catalog(seed=1).by_id != Catalog(seed=2).by_id


def test_merchant_ids_are_unique() -> None:
    catalog = Catalog()
    total = sum(len(v) for v in catalog.local.values())
    total += len(catalog.online) + len(catalog.online_risky)
    assert len(catalog.by_id) == total


def test_every_place_has_every_local_kind() -> None:
    catalog = Catalog(per_kind=3)
    for place in PLACES:
        assert {m.kind for m in catalog.local[place]} == set(LOCAL_KINDS)


def test_online_merchants_cover_normal_and_risky_kinds() -> None:
    catalog = Catalog(per_kind=2)
    assert {m.kind for m in catalog.online} == set(ONLINE_KINDS)
    assert {m.kind for m in catalog.online_risky} == set(RISKY_ONLINE_KINDS)
    assert all(m.online for m in catalog.online + catalog.online_risky)


def test_mcc_is_four_digits_and_coordinates_are_valid() -> None:
    for m in Catalog().by_id.values():
        assert re.fullmatch(r"\d{4}", m.mcc)
        assert -90 <= m.lat <= 90
        assert -180 <= m.lon <= 180


def test_local_merchants_stay_near_their_neighbourhood() -> None:
    catalog = Catalog()
    for name, merchants in catalog.local.items():
        place = PLACES[name]
        for m in merchants:
            assert abs(m.lat - place.lat) <= 0.02
            assert abs(m.lon - place.lon) <= 0.03
            assert m.country == place.country
