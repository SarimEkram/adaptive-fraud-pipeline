# ADR-0003: Redpanda as the event backbone

* Status: Accepted

## Context
Need a durable, replayable, partitioned log speaking the Kafka API, runnable on a laptop.

## Options considered
1. Apache Kafka: the standard; heavier to run locally.
2. Redpanda: Kafka-API compatible single binary, light, with a good web console.
3. Redis Streams: already have Redis, but weaker ecosystem and mixes hot-path and cold-path load on one dependency.
4. RabbitMQ: a queue, not a replayable log.

## Decision
Redpanda. Client code uses the standard Kafka API, so swapping to Apache Kafka is a config change.

## Consequences
Can say "Kafka" on a resume honestly (same API and semantics); must still understand partitions, consumer groups, offsets.
