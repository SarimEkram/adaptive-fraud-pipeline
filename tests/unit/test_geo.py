import pytest
from fraudcore.features.geo import EARTH_RADIUS_KM, haversine_km


def test_same_point_is_zero():
    assert haversine_km(43.65, -79.38, 43.65, -79.38) == pytest.approx(0.0)


def test_toronto_to_calgary():
    assert haversine_km(43.65, -79.38, 51.05, -114.07) == pytest.approx(2700, rel=0.03)


def test_distance_is_symmetric():
    a = haversine_km(43.65, -79.38, 49.28, -123.12)
    b = haversine_km(49.28, -123.12, 43.65, -79.38)
    assert a == pytest.approx(b)


def test_toronto_to_london():
    assert haversine_km(43.65, -79.38, 51.51, -0.13) == pytest.approx(5700, rel=0.02)


def test_one_degree_of_latitude_is_about_111_km():
    assert haversine_km(0, 0, 1, 0) == pytest.approx(111.2, rel=0.01)


def test_opposite_sides_of_the_earth_are_half_a_circumference_apart():
    assert haversine_km(0, 0, 0, 180) == pytest.approx(3.14159265 * EARTH_RADIUS_KM, rel=1e-6)


def test_short_distances_are_precise():
    # About 100 m north: the formula must not lose it to rounding.
    assert haversine_km(43.65, -79.38, 43.651, -79.38) == pytest.approx(0.111, rel=0.02)
