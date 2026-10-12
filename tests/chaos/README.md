One script per row in docs/06. Each scenario:
1. start traffic at a fixed rate with known txn_ids
2. inject the failure (stop container, add latency with `tc`, send poison message)
3. measure p99 and fallback-mode metrics during the incident
4. restore, wait for recovery
5. reconcile: sent txn_ids == decisions in Postgres, no duplicates
