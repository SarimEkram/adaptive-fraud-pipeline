"""Non-blocking Kafka publisher for ScoredEvents (ADR-0002, failure mode F2)."""

from __future__ import annotations

from fraudcore.schemas import ScoredEvent

TOPIC = "transactions.scored"


class EventPublisher:
    async def start(self) -> None:
        """TODO(phase 4): create AIOKafkaProducer (acks=all, linger_ms ~5, idempotence on)."""
        raise NotImplementedError

    def publish(self, event: ScoredEvent) -> None:
        """TODO(phase 4): fire and forget, key = card_id. Never await delivery on the hot path.

        Track a bounded in-flight count; if exceeded, drop and increment a metric.
        """
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError
