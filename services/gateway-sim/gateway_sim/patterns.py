"""Fraud patterns. Each returns the attack's transactions; the caller records ground truth.

Every pattern comes in an easy and a hard variant (about 30% hard) so that no single clue
gives all the fraud away.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta

import numpy as np
from fraudcore.schemas import Channel, Transaction

from gateway_sim.customers import CURRENCY, Customer, location_at, new_uuid
from gateway_sim.merchants import PLACES, TRIP_DESTINATIONS, Catalog, Merchant

_HARD_PROB = 0.3


class FraudPattern(ABC):
    """`now` is when the attack is triggered; each pattern says what that means for it."""

    name: str

    @abstractmethod
    def generate(
        self, victim: Customer, now: datetime, rng: np.random.Generator, catalog: Catalog
    ) -> list[Transaction]: ...


def _between(rng: np.random.Generator, low: int, high: int) -> int:
    """A whole number from low to high, both included."""
    return int(rng.integers(low, high + 1))


def _fraud_device(rng: np.random.Generator) -> str:
    return f"dev_fraud_{_between(rng, 0, 999_999_999):09d}"  # never seen on the victim's card


def _far_place(rng: np.random.Generator) -> tuple[float, float]:
    place = PLACES[TRIP_DESTINATIONS[int(rng.integers(len(TRIP_DESTINATIONS)))]]
    return place.lat, place.lon


def _choose(rng: np.random.Generator, pool: list[Merchant]) -> Merchant:
    return pool[int(rng.integers(len(pool)))]


def _unfamiliar(victim: Customer, pool: list[Merchant]) -> list[Merchant]:
    seen = set(victim.favourite_merchants)
    return [m for m in pool if m.merchant_id not in seen]


def _make(
    victim: Customer,
    merchant: Merchant,
    amount_cents: int,
    when: datetime,
    rng: np.random.Generator,
    where: tuple[float, float] | None = None,
    device: str | None = None,
) -> Transaction:
    """Build one fraudulent transaction. Online ones need `where` and `device`."""
    if merchant.online:
        if where is None or device is None:
            raise ValueError("online transactions need a location and a device")
        (lat, lon), channel = where, Channel.ECOMMERCE
    else:
        lat, lon, channel, device = merchant.lat, merchant.lon, Channel.CARD_PRESENT, None
    return Transaction(
        txn_id=new_uuid(rng),
        card_id=victim.card_id,
        customer_id=victim.customer_id,
        amount_cents=amount_cents,
        currency=CURRENCY,
        merchant_id=merchant.merchant_id,
        mcc=merchant.mcc,
        merchant_country=merchant.country,
        lat=lat,
        lon=lon,
        channel=channel,
        device_id=device,
        event_time=when,
    )


class StolenCardTravel(FraudPattern):
    """Card used far from home shortly after a normal purchase. Signal: implied speed.

    `now` must be the time of the victim's latest genuine in-person purchase at home; the
    attack starts a little after it. Easy: 20 to 90 minutes later, so the travel is
    impossible. Hard: 3 to 6 hours later, which a flight could just about explain, so the
    model must also lean on the large amount and the kind of shop.
    """

    name = "stolen_card_travel"

    def generate(
        self, victim: Customer, now: datetime, rng: np.random.Generator, catalog: Catalog
    ) -> list[Transaction]:
        if location_at(victim, now) != victim.home_area:
            return []
        city = TRIP_DESTINATIONS[int(rng.integers(len(TRIP_DESTINATIONS)))]
        hard = rng.random() < _HARD_PROB
        when = now + timedelta(minutes=_between(rng, 180, 360) if hard else _between(rng, 20, 90))

        txns: list[Transaction] = []
        for _ in range(_between(rng, 1, 3)):
            kind = rng.choice(["electronics", "clothing", "convenience"], p=[0.6, 0.2, 0.2])
            shops = [m for m in catalog.local[city] if m.kind == kind]  # convenience: gift cards
            amount = _between(rng, 15_000, 60_000)
            txns.append(_make(victim, _choose(rng, shops), amount, when, rng))
            when += timedelta(minutes=_between(rng, 5, 25))
        return txns


class CardTesting(FraudPattern):
    """Burst of tiny ecommerce charges, then maybe a large one. Signal: small_txn_count_10m.

    `now` is when the probing starts. Easy: 5 to 15 probes under $2 inside 2 to 10 minutes.
    Hard: 5 to 10 probes of $1 to $5, one every 5 to 10 minutes, which slips under both the
    "under $2" and the "burst" clues.
    """

    name = "card_testing"

    def generate(
        self, victim: Customer, now: datetime, rng: np.random.Generator, catalog: Catalog
    ) -> list[Transaction]:
        device, where = _fraud_device(rng), _far_place(rng)
        hard = rng.random() < _HARD_PROB
        targets = [
            _choose(rng, _unfamiliar(victim, catalog.online + catalog.online_risky))
            for _ in range(_between(rng, 1, 3))
        ]

        if hard:
            count = _between(rng, 5, 10)
            gaps = [_between(rng, 300, 600) for _ in range(count)]
            offsets = np.cumsum(gaps) - gaps[0]
            amounts = [_between(rng, 100, 500) for _ in range(count)]
        else:
            count = _between(rng, 5, 15)
            offsets = np.sort(rng.integers(0, _between(rng, 120, 600) + 1, count))
            amounts = [_between(rng, 50, 199) for _ in range(count)]

        txns = [
            _make(
                victim,
                _choose(rng, targets),
                amounts[i],
                now + timedelta(seconds=int(s)),
                rng,
                where,
                device,
            )
            for i, s in enumerate(offsets)
        ]
        if rng.random() < 0.5:  # the probes worked, so cash out
            shops = [m for m in catalog.online if m.kind == "online_electronics"]
            when = txns[-1].event_time + timedelta(minutes=_between(rng, 2, 5))
            txns.append(
                _make(
                    victim,
                    _choose(rng, shops),
                    _between(rng, 20_000, 50_000),
                    when,
                    rng,
                    where,
                    device,
                )
            )
        return txns


class AccountTakeover(FraudPattern):
    """New device, unfamiliar shops, large amounts. Signal: is_new_device + mcc risk.

    `now` is when the intruder gets in. Easy: 1 to 4 orders of $100 to $400 over up to three
    hours, 40% of them at crypto, gambling and similar shops. Hard: modest $40 to $90 orders
    in ordinary categories, so mostly the new device stands out. The intruder connects from
    far away half the time and through a local connection the other half.
    """

    name = "account_takeover"

    def generate(
        self, victim: Customer, now: datetime, rng: np.random.Generator, catalog: Catalog
    ) -> list[Transaction]:
        device = _fraud_device(rng)
        where = _far_place(rng) if rng.random() < 0.5 else (victim.home_lat, victim.home_lon)
        hard = rng.random() < _HARD_PROB
        count = _between(rng, 1, 4)
        offsets = np.sort(rng.integers(0, 180 * 60 + 1, count))

        if hard:
            usual_kinds = {
                m.kind
                for m in map(catalog.by_id.get, victim.favourite_merchants)
                if m is not None and m.online
            }
            pool = [m for m in catalog.online if m.kind in usual_kinds] or catalog.online
            amounts = [_between(rng, 4_000, 9_000) for _ in range(count)]
        else:
            pool = _unfamiliar(victim, catalog.online)
            amounts = [_between(rng, 10_000, 40_000) for _ in range(count)]

        txns: list[Transaction] = []
        for amount, s in zip(amounts, offsets, strict=True):
            risky = not hard and rng.random() < 0.4
            merchant = _choose(rng, catalog.online_risky if risky else pool)
            when = now + timedelta(seconds=int(s))
            txns.append(_make(victim, merchant, amount, when, rng, where, device))
        return txns


class MerchantCompromise(FraudPattern):
    """Stolen card details from a breached shop, used quietly online. Signal: across cards.

    The campaign (which shop was breached, and which customers had used it) is chosen by the
    caller; this produces one victim's misuse: one or two $80 to $250 online purchases at an
    unfamiliar shop from a new device, within six hours of `now`. Taken alone it looks like
    a mild account takeover. The real clue is that many victims share one shop in their past.
    """

    name = "merchant_compromise"

    def generate(
        self, victim: Customer, now: datetime, rng: np.random.Generator, catalog: Catalog
    ) -> list[Transaction]:
        device, where = _fraud_device(rng), _far_place(rng)
        pool = _unfamiliar(victim, catalog.online)
        txns: list[Transaction] = []
        for _ in range(1 if rng.random() < 0.7 else 2):
            when = now + timedelta(minutes=_between(rng, 0, 360))
            txns.append(
                _make(
                    victim,
                    _choose(rng, pool),
                    _between(rng, 8_000, 25_000),
                    when,
                    rng,
                    where,
                    device,
                )
            )
        return sorted(txns, key=lambda t: t.event_time)


PATTERNS: dict[str, FraudPattern] = {
    p.name: p for p in (StolenCardTravel(), CardTesting(), AccountTakeover(), MerchantCompromise())
}
