"""Geo helpers."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two points on the earth (a sphere here).

    The haversine formula is stable for short distances, where the plain "law of cosines"
    version loses precision. Toronto (43.65, -79.38) to Calgary (51.05, -114.07) is about
    2,700 km.
    """
    phi1, phi2 = radians(lat1), radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = radians(lon2 - lon1)
    a = sin(d_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(min(1.0, sqrt(a)))  # min() guards against rounding above 1
