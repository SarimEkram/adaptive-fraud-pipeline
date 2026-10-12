"""Synthetic places and merchants shared by normal customers and fraud patterns.

Everything here is deterministic: the same seed always builds the same catalog.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Place:
    name: str
    country: str
    lat: float
    lon: float
    utc_offset_hours: int  # standard time, no daylight saving (a simulation simplification)


PLACES: dict[str, Place] = {
    p.name: p
    for p in (
        # Toronto-area neighbourhoods: where customers live and shop day to day.
        Place("north_york", "CA", 43.7615, -79.4111, -5),
        Place("downtown", "CA", 43.6532, -79.3832, -5),
        Place("scarborough", "CA", 43.7731, -79.2578, -5),
        Place("etobicoke", "CA", 43.6205, -79.5132, -5),
        Place("mississauga", "CA", 43.5890, -79.6441, -5),
        # Far-away cities: legitimate trip destinations, also where stolen cards get used.
        Place("montreal", "CA", 45.5017, -73.5673, -5),
        Place("ottawa", "CA", 45.4215, -75.6972, -5),
        Place("calgary", "CA", 51.0447, -114.0719, -7),
        Place("vancouver", "CA", 49.2827, -123.1207, -8),
        Place("new_york", "US", 40.7128, -74.0060, -5),
    )
}

HOME_AREAS = ("north_york", "downtown", "scarborough", "etobicoke", "mississauga")
TRIP_DESTINATIONS = ("montreal", "ottawa", "calgary", "vancouver", "new_york")

# kind -> merchant category code (MCC), the 4-digit code card networks use.
LOCAL_KINDS: dict[str, str] = {
    "coffee": "5814",
    "restaurant": "5812",
    "convenience": "5499",
    "grocery": "5411",
    "transit": "4111",
    "gas": "5541",
    "pharmacy": "5912",
    "clothing": "5651",
    "electronics": "5732",
}
ONLINE_KINDS: dict[str, str] = {
    "marketplace": "5399",
    "food_delivery": "5812",
    "streaming": "4899",
    "online_electronics": "5732",
    "online_retail": "5311",
}
# Cash-like or hard-to-reverse goods. Honest customers almost never use these; fraudsters do.
RISKY_ONLINE_KINDS: dict[str, str] = {
    "digital_games": "5816",
    "crypto": "6051",
    "money_transfer": "4829",
    "gambling": "7995",
}

# How far a merchant can sit from the centre of its neighbourhood, in degrees
# (0.02 degrees of latitude is about 2.2 km).
_JITTER_LAT = 0.02
_JITTER_LON = 0.03


@dataclass(frozen=True)
class Merchant:
    merchant_id: str
    kind: str
    mcc: str
    country: str
    lat: float
    lon: float
    online: bool


class Catalog:
    """All merchants in the simulated world."""

    def __init__(self, seed: int = 42, per_kind: int = 6) -> None:
        rng = np.random.default_rng(seed)
        self.by_id: dict[str, Merchant] = {}
        self.local: dict[str, list[Merchant]] = {}
        self.online: list[Merchant] = []
        self.online_risky: list[Merchant] = []

        for place in PLACES.values():
            merchants: list[Merchant] = []
            for kind, mcc in LOCAL_KINDS.items():
                for i in range(per_kind):
                    merchants.append(
                        Merchant(
                            merchant_id=f"m_{place.name}_{kind}_{i}",
                            kind=kind,
                            mcc=mcc,
                            country=place.country,
                            lat=place.lat + float(rng.uniform(-_JITTER_LAT, _JITTER_LAT)),
                            lon=place.lon + float(rng.uniform(-_JITTER_LON, _JITTER_LON)),
                            online=False,
                        )
                    )
            self.local[place.name] = merchants

        # Online merchants have no storefront; the location is a placeholder head office.
        hq = PLACES["downtown"]
        for kinds, bucket in ((ONLINE_KINDS, self.online), (RISKY_ONLINE_KINDS, self.online_risky)):
            for kind, mcc in kinds.items():
                for i in range(per_kind):
                    bucket.append(
                        Merchant(
                            merchant_id=f"m_online_{kind}_{i}",
                            kind=kind,
                            mcc=mcc,
                            country="CA",
                            lat=hq.lat,
                            lon=hq.lon,
                            online=True,
                        )
                    )

        for merchants in self.local.values():
            for m in merchants:
                self.by_id[m.merchant_id] = m
        for m in self.online + self.online_risky:
            self.by_id[m.merchant_id] = m
