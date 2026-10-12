"""Online card-state store backed by Redis. Key: card:{card_id}:state (see docs/03)."""

from __future__ import annotations

from redis.asyncio import Redis

from fraudcore.features.state import CardState


def state_key(card_id: str) -> str:
    return f"card:{{{card_id}}}:state"  # hash tag keeps one card on one cluster shard


class CardStateStore:
    def __init__(self, redis: Redis, ttl_s: int) -> None:
        self._redis = redis
        self._ttl_s = ttl_s

    async def load(self, card_id: str) -> CardState:
        """TODO(phase 4): GET the key; return empty CardState(card_id) if missing."""
        raise NotImplementedError

    async def save(self, state: CardState) -> None:
        """TODO(phase 4): SET with TTL. Phase 5: handle concurrent writers (failure mode F10)."""
        raise NotImplementedError
