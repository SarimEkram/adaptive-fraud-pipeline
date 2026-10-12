# ADR-0002: Synchronous scoring, asynchronous everything else

* Status: Accepted

## Context
A card authorization needs an answer in the request. Analytics, storage, labels, and training do not.

## Options considered
1. Stream-first: gateway publishes to Kafka, scorer consumes, decision returned via another topic. Natural for streaming, but adds broker latency to the decision and makes request/response awkward.
2. Fully synchronous: scorer writes to Postgres before responding. Simple, but the database is on the hot path.
3. Sync scoring API with Redis state, publish decisions to Kafka asynchronously.

## Decision
Option 3. This mirrors how real authorization systems work.

## Consequences
* Hot path depends only on the scorer and Redis.
* Kafka publishing must never block the response (buffered producer, bounded memory).
* Everything downstream must tolerate at-least-once delivery.

## How I would explain this in an interview
The decision is a request/response problem with a hard deadline, so it is synchronous and touches only in-memory state. Everything else is a data problem, so it rides an event log where throughput and replayability matter more than latency.
