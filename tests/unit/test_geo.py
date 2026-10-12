import pytest

from fraudcore.features.geo import haversine_km

pytestmark = pytest.mark.xfail(reason="phase 2: implement haversine_km", raises=NotImplementedError)


def test_same_point_is_zero():
    assert haversine_km(43.65, -79.38, 43.65, -79.38) == pytest.approx(0.0)


def test_toronto_to_calgary():
    assert haversine_km(43.65, -79.38, 51.05, -114.07) == pytest.approx(2700, rel=0.03)
