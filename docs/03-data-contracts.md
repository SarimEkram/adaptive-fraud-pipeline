# 03 Data contracts

Contracts are code: the source of truth is `libs/fraudcore/fraudcore/schemas.py`. This doc explains the why.

## Rules

* Money is **integer cents** (`amount_cents`), never float (ADR-0007).
* Timestamps are UTC, ISO 8601. `event_time` is when the card was used; `decided_at` is when we decided. Never mix them.
* Every event has `schema_version`. Additive changes (new optional field) keep the version; anything else bumps it and consumers must handle both during migration.
* IDs are opaque. `card_id` is a token, never a card number.

## Transaction (request to `POST /v1/score`)

| Field | Type | Notes |
|---|---|---|
| schema_version | int | currently 1 |
| txn_id | UUID | idempotency key |
| card_id | str | partition key everywhere |
| customer_id | str | |
| amount_cents | int > 0 | |
| currency | str(3) | ISO 4217 |
| merchant_id | str | |
| mcc | str(4) | merchant category code; drives category risk |
| merchant_country | str(2) | ISO 3166 alpha-2 |
| lat, lon | float | merchant location |
| channel | enum | card_present, ecommerce |
| device_id | str or null | ecommerce only |
| event_time | datetime | UTC |

## Decision (response)

| Field | Type | Notes |
|---|---|---|
| txn_id | UUID | |
| action | enum | APPROVE, REVIEW, DECLINE |
| score | float 0..1 | champion fraud probability |
| model_version | str | |
| rules_fired | list[str] | |
| reasons | list[Reason] | top 3 by contribution |
| shadow_score, shadow_model_version | float, str or null | challenger, logged only |
| latency_ms | float | measured inside the service |
| decided_at | datetime | |

## Kafka topics

| Topic | Key | Producer | Consumers | Partitions |
|---|---|---|---|---|
| transactions.scored | card_id | scoring | event-sink, analyst-api, ml-platform drift | 6 |
| labels.chargeback | card_id | gateway-sim | event-sink | 3 |
| labels.analyst | card_id | analyst-api | event-sink | 3 |
| transactions.scored.dlq | card_id | event-sink | humans | 1 |

Keyed by `card_id` so per-card ordering holds. Delivery is at-least-once; consumers must be idempotent.

## Redis keys

| Key | Type | TTL | Contents |
|---|---|---|---|
| `idem:{txn_id}` | string | 24 h | serialized Decision |
| `card:{card_id}:state` | string (JSON) | 30 d | serialized `CardState` |

Phase 4 starts with one JSON blob per card: simplest, one round trip, atomic per key. Phase 5 may split hot fields into sorted sets and hashes if profiling says so; record that as an ADR.

## Postgres tables

See `infra/postgres/init.sql`. Summary: `transactions`, `decisions`, `labels`, `review_queue`, `model_versions`. Every write is an upsert keyed by `txn_id` (or `txn_id, source` for labels) so replaying a topic is safe.
