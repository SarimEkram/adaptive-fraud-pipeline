Dashboards to build in Phase 3 and 5 (export JSON here):
* Scoring latency p50/p95/p99 from `score_latency_seconds`
* Decisions per second by action
* Kafka consumer lag (from Redpanda metrics)
* Fallback mode active, dropped events
PromQL p99: histogram_quantile(0.99, sum(rate(score_latency_seconds_bucket[1m])) by (le))
