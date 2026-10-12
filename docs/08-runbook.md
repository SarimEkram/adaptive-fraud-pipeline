# 08 Runbook

## Run

```bash
make up            # everything
make topics        # first run only
make sim RATE=200  # transactions per second
make logs s=scoring
make down          # stop, keep volumes
make nuke          # stop and delete all data
```

| URL | What |
|---|---|
| http://localhost:8000/docs | scoring API |
| http://localhost:8001/docs | analyst API |
| http://localhost:8080 | Redpanda console (topics, messages, lag) |
| http://localhost:9090 | Prometheus |
| http://localhost:3001 | Grafana (admin / admin) |
| http://localhost:3000 | dashboard |

## The 3-minute demo

1. Dashboard open: normal traffic flowing, mostly APPROVE, latency chart flat.
2. Click **Launch stolen-card attack**. Red DECLINEs appear with `IMPOSSIBLE_TRAVEL`.
3. Click a flagged transaction: show the reason codes and score.
4. Open the review queue, label two cases. Show the label landing in Postgres.
5. Start the **adaptive attacker**. Show PSI alert, challenger training, shadow scores, promotion.
6. Close on the metrics page: p99, PR-AUC, cost vs rules baseline.

## Break it on purpose

```bash
make chaos-redis      # stop redis 30 s; expect fallback mode, then recovery
make chaos-kafka      # stop redpanda 30 s; decisions continue, events buffered
make chaos-postgres   # stop postgres 30 s; sink lag grows, then catches up
make bench            # load test, writes results to benchmarks/results/
```

After each, check: decisions sent vs stored (no loss, no duplicates), p99 during the incident, recovery time.
