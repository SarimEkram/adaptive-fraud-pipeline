"""Synthetic customer population. Realistic normal behaviour is what makes fraud detectable."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

import numpy as np
from fraudcore.schemas import Channel, Transaction

from gateway_sim.merchants import HOME_AREAS, PLACES, TRIP_DESTINATIONS, Catalog, Merchant

SIM_START = date(2026, 1, 1)
CURRENCY = "CAD"  # simplification: every amount is in CAD, even in New York

# Relative chance of shopping in each local hour (index 0 = midnight): quiet at night,
# busier at lunch and early evening. Each customer gets a jittered copy of this shape.
_BASE_HOUR_WEIGHTS = (
    0.3, 0.2, 0.15, 0.1, 0.1, 0.2, 0.5, 1.0, 1.5, 1.5, 1.5, 2.0,
    2.5, 2.0, 1.5, 1.5, 1.8, 2.2, 2.5, 2.0, 1.5, 1.0, 0.7, 0.5,
)  # fmt: skip

# Trips: every `trip_period_days` a customer leaves at 06:00 Toronto time, arrives six hours
# later, and comes back the same way. Computed from the clock alone, so it needs no state.
_TRIP_EPOCH = datetime(2025, 1, 1, tzinfo=UTC)
_DEPART_HOUR_UTC = 11  # 06:00 at UTC-5
_TRANSIT = timedelta(hours=6)

_MIN_REGULAR_CENTS = 200  # honest purchases are at least $2, so "under $2" stays suspicious
_MAX_REGULAR_CENTS = 60_000
_BIG_MEAN_CENTS = 15_000  # the $150 headphones
_BIG_MIN_CENTS = 6_000
_BURST_PROB = 0.08  # chance per day of a quick run of small, familiar purchases
_BURST_KINDS = {"coffee", "transit", "convenience", "restaurant"}


@dataclass(frozen=True)
class _Segment:
    share: float
    mean_amount_cents: tuple[int, int]
    txns_per_day: tuple[float, float]
    online_share: tuple[float, float]
    trip_period_days: tuple[int, int]


SEGMENTS: dict[str, _Segment] = {
    "student": _Segment(0.25, (700, 1_100), (1.5, 3.0), (0.60, 0.85), (120, 180)),
    "commuter": _Segment(0.40, (1_100, 1_800), (1.2, 2.5), (0.45, 0.75), (90, 120)),
    "family": _Segment(0.25, (2_200, 3_500), (1.0, 2.0), (0.35, 0.60), (130, 200)),
    "traveller": _Segment(0.10, (1_400, 2_400), (1.5, 2.5), (0.40, 0.70), (40, 70)),
}


def _normalized(weights: tuple[float, ...] | list[float]) -> list[float]:
    total = sum(weights)
    return [w / total for w in weights]


@dataclass
class Customer:
    customer_id: str
    card_id: str
    home_country: str
    home_lat: float
    home_lon: float
    segment: str = "commuter"
    home_area: str = "north_york"
    anchor_area: str = "downtown"  # where they commute or hang out
    favourite_merchants: list[str] = field(default_factory=list)
    devices: list[str] = field(default_factory=lambda: ["dev_phone", "dev_laptop"])
    replacement_phone: str | None = None  # a new phone bought on upgrade_day
    upgrade_day: date | None = None
    mean_amount_cents: int = 1_400
    amount_sigma: float = 0.7
    txns_per_day: float = 2.0
    online_share: float = 0.6
    big_purchase_prob: float = 0.02
    hour_weights: list[float] = field(default_factory=lambda: _normalized(_BASE_HOUR_WEIGHTS))
    trip_period_days: int = 105
    trip_offset_days: int = 0
    trip_length_days: int = 4
    trip_destination_offset: int = 0


def _sample(rng: np.random.Generator, pool: list[Merchant], k: int) -> list[Merchant]:
    picks = rng.choice(len(pool), size=min(k, len(pool)), replace=False)
    return [pool[int(i)] for i in picks]


def _choose(rng: np.random.Generator, pool: list[Merchant]) -> Merchant:
    return pool[int(rng.integers(len(pool)))]


def generate_population(
    n: int,
    seed: int = 42,
    catalog: Catalog | None = None,
    start: date = SIM_START,
    days: int = 90,
) -> list[Customer]:
    """Varied spenders (students, commuters, families, travellers), mostly domestic."""
    catalog = catalog or Catalog(seed)
    rng = np.random.default_rng([seed, 1])
    names = list(SEGMENTS)
    shares = [SEGMENTS[s].share for s in names]
    customers: list[Customer] = []

    for i in range(n):
        segment = names[int(rng.choice(len(names), p=shares))]
        cfg = SEGMENTS[segment]
        home_area = HOME_AREAS[int(rng.integers(len(HOME_AREAS)))]
        anchor_area = "downtown" if home_area != "downtown" else "north_york"
        home = PLACES[home_area]

        favourites = (
            _sample(rng, catalog.local[home_area], 8)
            + _sample(rng, catalog.local[anchor_area], 4)
            + _sample(rng, catalog.online, 3)
        )

        weights = np.array(_BASE_HOUR_WEIGHTS) * rng.lognormal(0.0, 0.4, 24)
        if rng.random() < 0.15:  # night owls
            weights[[22, 23, 0, 1, 2]] *= 4
        period = int(rng.integers(cfg.trip_period_days[0], cfg.trip_period_days[1] + 1))

        customer = Customer(
            customer_id=f"cust_{i:05d}",
            card_id=f"card_{i:05d}",
            home_country=home.country,
            home_lat=home.lat + float(rng.uniform(-0.01, 0.01)),
            home_lon=home.lon + float(rng.uniform(-0.01, 0.01)),
            segment=segment,
            home_area=home_area,
            anchor_area=anchor_area,
            favourite_merchants=[m.merchant_id for m in favourites],
            devices=[f"dev_{i:05d}_phone", f"dev_{i:05d}_laptop"],
            mean_amount_cents=int(rng.integers(*cfg.mean_amount_cents)),
            txns_per_day=float(rng.uniform(*cfg.txns_per_day)),
            online_share=float(rng.uniform(*cfg.online_share)),
            big_purchase_prob=float(rng.uniform(0.01, 0.03)),
            hour_weights=_normalized(weights.tolist()),
            trip_period_days=period,
            trip_offset_days=int(rng.integers(0, period)),
            trip_length_days=int(rng.integers(3, 8)),
            trip_destination_offset=int(rng.integers(len(TRIP_DESTINATIONS))),
        )
        if rng.random() < 0.4:  # a new phone, and so a new device, sometime during the run
            customer.replacement_phone = f"dev_{i:05d}_phone2"
            customer.upgrade_day = start + timedelta(days=int(rng.integers(5, max(6, days - 5))))
        customers.append(customer)
    return customers


def location_at(customer: Customer, t: datetime) -> str | None:
    """Name of the place the customer is at time t, or None while they are in transit."""
    days_since_epoch = (t - _TRIP_EPOCH) / timedelta(days=1)
    cycle = math.floor((days_since_epoch - customer.trip_offset_days) / customer.trip_period_days)
    cycle_start = customer.trip_offset_days + cycle * customer.trip_period_days
    depart = _TRIP_EPOCH + timedelta(days=cycle_start, hours=_DEPART_HOUR_UTC)
    arrive = depart + _TRANSIT
    leave = depart + timedelta(days=customer.trip_length_days)
    back = leave + _TRANSIT

    if t < depart or t >= back:
        return customer.home_area
    if t < arrive or t >= leave:
        return None
    return TRIP_DESTINATIONS[(cycle + customer.trip_destination_offset) % len(TRIP_DESTINATIONS)]


def _coords_at(customer: Customer, place: str) -> tuple[float, float]:
    if place == customer.home_area:
        return customer.home_lat, customer.home_lon
    return PLACES[place].lat, PLACES[place].lon


def new_uuid(rng: np.random.Generator) -> UUID:
    return UUID(bytes=rng.bytes(16), version=4)  # random but reproducible from the seed


def _lognormal_cents(rng: np.random.Generator, mean_cents: float, sigma: float) -> int:
    mu = math.log(mean_cents) - sigma**2 / 2  # so the mean, not the median, is mean_cents
    return int(round(float(rng.lognormal(mu, sigma))))


def _pick_device(customer: Customer, now: datetime, rng: np.random.Generator) -> str:
    if rng.random() < 0.7:  # the phone is used more than the laptop
        upgraded = customer.upgrade_day is not None and now.date() >= customer.upgrade_day
        if upgraded and customer.replacement_phone:
            return customer.replacement_phone
        return customer.devices[0]
    return customer.devices[1]


def _pick_merchant(
    customer: Customer,
    place: str,
    online: bool,
    big: bool,
    rng: np.random.Generator,
    catalog: Catalog,
) -> Merchant:
    favourites = [catalog.by_id[m] for m in customer.favourite_merchants]
    if online:
        if big:
            return _choose(rng, [m for m in catalog.online if m.kind == "online_electronics"])
        if rng.random() < 0.002:  # honest people very rarely touch crypto or gambling
            return _choose(rng, catalog.online_risky)
        online_favs = [m for m in favourites if m.online]
        if online_favs and rng.random() < 0.7:
            return _choose(rng, online_favs)
        return _choose(rng, catalog.online)

    if place == customer.home_area:
        pool = catalog.local[customer.home_area] + catalog.local[customer.anchor_area]
        local_favs = [m for m in favourites if not m.online]
        if not big and local_favs and rng.random() < 0.75:
            return _choose(rng, local_favs)
    else:  # on a trip: no favourites, just whatever is nearby
        pool = catalog.local[place]
    if big:
        pool = [m for m in pool if m.kind == "electronics"]
    return _choose(rng, pool)


def normal_transaction(
    customer: Customer, now: datetime, rng: np.random.Generator, catalog: Catalog
) -> Transaction | None:
    """One honest purchase at time `now`, or None if the customer is in transit."""
    place = location_at(customer, now)
    if place is None:
        return None

    online = rng.random() < customer.online_share
    new_phone_day = online and customer.upgrade_day == now.date()
    big = rng.random() < (0.6 if new_phone_day else customer.big_purchase_prob)
    merchant = _pick_merchant(customer, place, online, big, rng, catalog)

    if big:
        amount = max(_lognormal_cents(rng, _BIG_MEAN_CENTS, 0.4), _BIG_MIN_CENTS)
    else:
        amount = _lognormal_cents(rng, customer.mean_amount_cents, customer.amount_sigma)
        amount = min(max(amount, _MIN_REGULAR_CENTS), _MAX_REGULAR_CENTS)

    if online:
        lat, lon = _coords_at(customer, place)  # where the customer is, like an IP lookup
        channel, device = Channel.ECOMMERCE, _pick_device(customer, now, rng)
    else:
        lat, lon = merchant.lat, merchant.lon
        channel, device = Channel.CARD_PRESENT, None

    return Transaction(
        txn_id=new_uuid(rng),
        card_id=customer.card_id,
        customer_id=customer.customer_id,
        amount_cents=amount,
        currency=CURRENCY,
        merchant_id=merchant.merchant_id,
        mcc=merchant.mcc,
        merchant_country=merchant.country,
        lat=lat,
        lon=lon,
        channel=channel,
        device_id=device,
        event_time=now,
    )


def burst_transactions(
    customer: Customer, now: datetime, rng: np.random.Generator, catalog: Catalog
) -> list[Transaction]:
    """2 to 4 small purchases within about 12 minutes at familiar shops, in person.

    The honest look-alike of card testing: also small and quick, but familiar and local.
    """
    if location_at(customer, now) != customer.home_area:
        return []
    familiar = [
        catalog.by_id[m]
        for m in customer.favourite_merchants
        if not catalog.by_id[m].online and catalog.by_id[m].kind in _BURST_KINDS
    ] or [m for m in catalog.local[customer.home_area] if m.kind in _BURST_KINDS]

    txns: list[Transaction] = []
    t = now
    for _ in range(int(rng.integers(2, 5))):
        merchant = _choose(rng, familiar)
        txns.append(
            Transaction(
                txn_id=new_uuid(rng),
                card_id=customer.card_id,
                customer_id=customer.customer_id,
                amount_cents=int(rng.integers(250, 701)),
                currency=CURRENCY,
                merchant_id=merchant.merchant_id,
                mcc=merchant.mcc,
                merchant_country=merchant.country,
                lat=merchant.lat,
                lon=merchant.lon,
                channel=Channel.CARD_PRESENT,
                device_id=None,
                event_time=t,
            )
        )
        t += timedelta(minutes=int(rng.integers(1, 5)))
    return txns


def _random_time_on(customer: Customer, day: date, rng: np.random.Generator) -> datetime:
    """A moment on `day` (Toronto clock) drawn from the customer's hourly habits, in UTC."""
    hour = int(rng.choice(24, p=customer.hour_weights))
    local = datetime.combine(
        day, time(hour, int(rng.integers(60)), int(rng.integers(60))), tzinfo=UTC
    )
    return local - timedelta(hours=PLACES[customer.home_area].utc_offset_hours)


def daily_transactions(
    customer: Customer, day: date, rng: np.random.Generator, catalog: Catalog
) -> list[Transaction]:
    """All honest transactions for one customer on one day, in time order."""
    txns: list[Transaction] = []
    for _ in range(int(rng.poisson(customer.txns_per_day))):
        txn = normal_transaction(customer, _random_time_on(customer, day, rng), rng, catalog)
        if txn is not None:
            txns.append(txn)
    if rng.random() < _BURST_PROB:
        txns.extend(burst_transactions(customer, _random_time_on(customer, day, rng), rng, catalog))
    return sorted(txns, key=lambda t: t.event_time)
