# ADR-0004: Redis for online feature state

* Status: Accepted

## Context
Velocity and history features need per-card state read and written within a few milliseconds.

## Options considered
1. Postgres queries at request time: simple, too slow and puts the DB on the hot path.
2. In-process memory: fastest, but lost on restart and breaks with multiple replicas.
3. Redis: sub-millisecond, shared across replicas, TTLs built in.

## Decision
Redis, starting with one JSON blob per card (`card:{card_id}:state`).

## Consequences
* Redis is now a hot-path dependency: needs fallback (F1).
* Concurrent updates per card need a strategy (F10, Phase 5).
* Start simple; optimize data structures only with profiling evidence.
