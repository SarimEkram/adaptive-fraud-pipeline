# ADR-0006: One feature implementation for online and offline

* Status: Accepted

## Context
The most common way production ML fails silently is training-serving skew: training features computed in pandas, serving features computed differently in the service.

## Decision
Features are two pure functions in `fraudcore.features`:
`compute_features(txn, state) -> dict` and `update_state(txn, state) -> CardState`.
Online: state loaded from Redis. Offline: events replayed in event-time order with state held in memory.

## Consequences
* Skew is prevented by construction, and a parity test proves it.
* Offline feature building is a sequential replay, slower than vectorized pandas. Acceptable at this scale; partition by card to parallelize if needed.
* Point-in-time correctness comes for free if compute runs before update.
