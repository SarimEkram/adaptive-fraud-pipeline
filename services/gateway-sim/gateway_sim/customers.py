"""Synthetic customer population. Realistic normal behaviour is what makes fraud detectable."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from fraudcore.schemas import Transaction


@dataclass
class Customer:
    customer_id: str
    card_id: str
    home_country: str
    home_lat: float
    home_lon: float
    favourite_merchants: list[str] = field(default_factory=list)
    devices: list[str] = field(default_factory=list)
    mean_amount_cents: int = 4_000
    txns_per_day: float = 3.0


def generate_population(n: int, seed: int = 42) -> list[Customer]:
    """TODO(phase 1): varied spenders (students, families, travellers), mostly domestic."""
    raise NotImplementedError


def normal_transaction(customer: Customer, now: datetime) -> Transaction:
    """TODO(phase 1): mostly favourite merchants near home, daytime-weighted, log-normal amounts."""
    raise NotImplementedError
