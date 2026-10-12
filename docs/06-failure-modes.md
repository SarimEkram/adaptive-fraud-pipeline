# 06 Failure modes

Every row needs a chaos test in `tests/chaos/` before Phase 5 is done. "Proposed" behaviour is a starting point; final calls are recorded in ADR-0008.

| # | Failure | Detection | Proposed behaviour | Why | Test |
|---|---|---|---|---|---|
| F1 | Redis down or slow | timeout > 5 ms, circuit breaker | Rules-only mode with stateless rules; fail open under $100, REVIEW above | customer impact vs fraud loss; see ADR-0008 | `make chaos-redis` |
| F2 | Kafka unavailable | producer errors, buffer filling | Keep deciding; buffer in memory up to a bound, then drop events and count them | decisions must not wait on analytics | `make chaos-kafka` |
| F3 | Postgres down | sink errors | Sink pauses consumption; Kafka retains events; resume catches up | Kafka is the buffer | `make chaos-postgres` |
| F4 | Model file missing or corrupt | load error at startup or reload | Keep previous model; if none, rules-only and readiness false | never serve garbage | unit + chaos |
| F5 | Duplicate request (gateway retry) | idempotency key exists | Return stored decision, do not touch state | at-least-once upstream | integration |
| F6 | Duplicate event in Kafka | upsert conflict | `ON CONFLICT DO NOTHING` | at-least-once delivery | integration |
| F7 | Poison message | deserialization error | Send to DLQ, commit offset, alert | one bad event must not block a partition | integration |
| F8 | Out-of-order events for a card | event_time < last_ts | Score normally; do not move `last_*` backwards | network reordering | unit |
| F9 | Overload | queue depth, p99 rising | Shed challenger shadow scoring first, then return 503 for gateway retry | protect the champion path | load test |
| F10 | Concurrent requests for same card | lost update on state | Phase 5 decision: WATCH/MULTI, Lua, or per-card routing | correctness of velocity | concurrency test |
| F11 | Drift (new attack) | PSI alert, recall drop | Retrain, shadow, promote via gates | adaptation goal | `drift-shift` scenario |
