# scoring (hot path)

`POST /v1/score` takes a Transaction, returns a Decision. Budget: p99 < 50 ms (docs/02 section 5).

| File | Role | Owner |
|---|---|---|
| main.py | FastAPI app, routes, lifespan, metrics | Claude can help |
| pipeline.py | the 9 steps of a decision | **you write** |
| rules.py | hard rules | **you write** |
| decision.py | thresholds to action, reason codes | **you write** |
| model.py | load champion/challenger from registry | shared |
| publisher.py | non-blocking Kafka producer | Claude can help |

The Owner column is the original designation. Current working mode (see `CLAUDE.md`): Claude writes the code, explains it line by line, and the author restates the key idea.

Rule: nothing in this service may block on Postgres or wait on Kafka.
