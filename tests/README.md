# Tests

| Folder | What | When it runs |
|---|---|---|
| unit/ | pure functions: features, geo, rules, decision, PSI | every commit |
| contract/ | schemas, online/offline parity, every decision has reasons | every commit |
| integration/ | services against real Redis/Kafka/Postgres (compose) | before merging a phase |
| chaos/ | failure modes from docs/06 | Phase 5 onward |

Tests for unbuilt features are marked `xfail` with the phase that removes the mark. When a phase is done, delete its xfail marks: the tests become your exit criteria.
