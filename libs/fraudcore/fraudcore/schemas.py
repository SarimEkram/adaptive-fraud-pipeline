"""Data contracts. Source of truth for every service. See docs/03-data-contracts.md."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1


class Channel(StrEnum):
    CARD_PRESENT = "card_present"
    ECOMMERCE = "ecommerce"


class Action(StrEnum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    DECLINE = "DECLINE"


class LabelSource(StrEnum):
    CHARGEBACK = "chargeback"
    ANALYST = "analyst"


class _Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Transaction(_Contract):
    schema_version: Literal[1] = SCHEMA_VERSION
    txn_id: UUID
    card_id: str = Field(min_length=1)
    customer_id: str = Field(min_length=1)
    amount_cents: int = Field(gt=0, strict=True)  # ADR-0007: never float
    currency: str = Field(min_length=3, max_length=3)
    merchant_id: str
    mcc: str = Field(pattern=r"^\d{4}$")
    merchant_country: str = Field(min_length=2, max_length=2)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    channel: Channel
    device_id: str | None = None
    event_time: datetime  # UTC, when the card was used


class Reason(_Contract):
    code: str  # e.g. IMPOSSIBLE_TRAVEL
    feature: str
    contribution: float


class Decision(_Contract):
    schema_version: Literal[1] = SCHEMA_VERSION
    txn_id: UUID
    action: Action
    score: float = Field(ge=0.0, le=1.0)
    model_version: str
    rules_fired: list[str] = Field(default_factory=list)
    reasons: list[Reason] = Field(default_factory=list)
    shadow_score: float | None = None
    shadow_model_version: str | None = None
    latency_ms: float
    decided_at: datetime


class ScoredEvent(_Contract):
    """Payload on the transactions.scored topic."""

    schema_version: Literal[1] = SCHEMA_VERSION
    transaction: Transaction
    decision: Decision
    features: dict[str, float]  # logged so drift and audits use exactly what the model saw


class Label(_Contract):
    schema_version: Literal[1] = SCHEMA_VERSION
    txn_id: UUID
    card_id: str
    is_fraud: bool
    source: LabelSource
    labeled_at: datetime
