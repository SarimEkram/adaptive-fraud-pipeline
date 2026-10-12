"""These pass today: the contracts are already defined."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fraudcore.schemas import Channel, Transaction
from pydantic import ValidationError


def base(**overrides):
    data = dict(
        txn_id=uuid4(),
        card_id="c1",
        customer_id="u1",
        amount_cents=1299,
        currency="CAD",
        merchant_id="m1",
        mcc="5411",
        merchant_country="CA",
        lat=43.65,
        lon=-79.38,
        channel=Channel.CARD_PRESENT,
        event_time=datetime.now(UTC),
    )
    data.update(overrides)
    return data


def test_valid_transaction():
    assert Transaction(**base()).amount_cents == 1299


def test_float_money_rejected():
    with pytest.raises(ValidationError):
        Transaction(**base(amount_cents=12.99))


def test_negative_amount_rejected():
    with pytest.raises(ValidationError):
        Transaction(**base(amount_cents=-5))


def test_unknown_field_rejected():
    with pytest.raises(ValidationError):
        Transaction(**base(surprise="x"))
