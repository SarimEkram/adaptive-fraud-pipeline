"""Fraud patterns. Each returns the attack's transactions; the caller records ground truth."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from fraudcore.schemas import Transaction

from gateway_sim.customers import Customer


class FraudPattern(ABC):
    name: str

    @abstractmethod
    def generate(self, victim: Customer, now: datetime) -> list[Transaction]: ...


class StolenCardTravel(FraudPattern):
    """Card used far from home shortly after a normal purchase. Signal: implied speed."""

    name = "stolen_card_travel"

    def generate(self, victim: Customer, now: datetime) -> list[Transaction]:
        raise NotImplementedError  # TODO(phase 1)


class CardTesting(FraudPattern):
    """Burst of tiny ecommerce charges, then a large one. Signal: small_txn_count_10m."""

    name = "card_testing"

    def generate(self, victim: Customer, now: datetime) -> list[Transaction]:
        raise NotImplementedError  # TODO(phase 1)


class AccountTakeover(FraudPattern):
    """New device, high-risk category, large amount. Signal: is_new_device + mcc risk."""

    name = "account_takeover"

    def generate(self, victim: Customer, now: datetime) -> list[Transaction]:
        raise NotImplementedError  # TODO(phase 1)


class MerchantCompromise(FraudPattern):
    """Many cards that shopped at one merchant start showing fraud.

    Signal: harder; a stretch goal.
    """

    name = "merchant_compromise"

    def generate(self, victim: Customer, now: datetime) -> list[Transaction]:
        raise NotImplementedError  # TODO(phase 1)


PATTERNS: dict[str, FraudPattern] = {
    p.name: p for p in (StolenCardTravel(), CardTesting(), AccountTakeover(), MerchantCompromise())
}
