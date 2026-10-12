# 07 Roadmap

Each phase has a deliverable, exit criteria, and questions you must answer out loud without notes before moving on. Write a design note (`docs/design-notes/`) at the start of every phase.

**Ownership rule.** "You write" means you type the logic yourself; Claude may review it and explain. "Claude can help" means generate, then read every line.

---

## Phase 0: Foundations (week 1)

* Deliverable: this scaffold runs; `make up` starts infra; CI is green.
* You write: nothing yet. Read every doc in `docs/`.
* Exit: you can explain the architecture diagram and the hot vs cold path split.

## Phase 1: Synthetic world (weeks 2 to 3)

* Deliverable: `gateway-sim` writes realistic customers and 4 fraud patterns to a Parquet file (no network yet).
* You write: `customers.py`, `patterns.py`.
* Claude can help: CLI wiring, Parquet output.
* Exit criteria: fraud rate about 1%; plot of normal vs fraud spending looks plausible.
* Must explain: what makes each pattern detectable; why realistic normal behaviour matters as much as the fraud.

## Phase 2: Offline model (weeks 4 to 5)

* Deliverable: `ml-platform replay`, `train`, `evaluate` produce the model-card results table.
* You write: `features/compute.py`, `features/geo.py`, `replay.py`, `evaluate.py`, threshold selection from the cost matrix.
* Claude can help: plotting, LightGBM boilerplate.
* Exit criteria: LightGBM beats rules on PR-AUC and expected cost; time-based split; feature unit tests pass.
* Must explain: PR-AUC vs ROC-AUC, why time split, point-in-time correctness, how thresholds came from costs.

## Phase 3: Scoring service (weeks 6 to 7)

* Deliverable: `POST /v1/score` returns decisions with reasons; latency histogram exported.
* You write: `pipeline.py`, `rules.py`, `decision.py`, reason-code mapping.
* Claude can help: FastAPI app wiring, Prometheus setup, Dockerfile.
* Exit criteria: p99 measured and recorded; contract tests pass.
* Must explain: p50 vs p99, where every millisecond goes, why contributions come from TreeSHAP.

## Phase 4: Real-time pipeline (weeks 8 to 10)

* Deliverable: state in Redis, idempotency, decisions published to Kafka, sink writes Postgres, simulator streams live.
* You write: `stores/redis_state.py`, idempotency, event-sink consumer logic, parity test.
* Claude can help: compose config, topic scripts, aiokafka boilerplate.
* Exit criteria: parity test green; replaying a topic twice leaves Postgres unchanged.
* Must explain: training-serving skew, at-least-once delivery, why keys are card_id, idempotency end to end.

## Phase 5: Reliability (weeks 11 to 12)

* Deliverable: every row in doc 06 has behaviour implemented and a chaos test.
* You write: circuit breaker, fallback mode, concurrency control (F10), ADR-0008 final decision.
* Exit criteria: `make chaos` green; load test hits S1 and S2.
* Must explain: every failure mode and why that behaviour.

## Phase 6: Analyst loop and dashboard (weeks 13 to 14)

* Deliverable: live feed, attack buttons, threshold sliders, review queue that emits labels.
* You write: review-queue logic and label flow in `analyst-api`.
* Claude can help: most of the React UI.
* Exit criteria: the 3-minute demo in the runbook works end to end.

## Phase 7: Adaptation (weeks 15 to 17)

* Deliverable: adversarial attacker, PSI drift detection, Isolation Forest, automated retrain, shadow, promote.
* You write: `drift.py`, `promote.py` gates, shadow comparison.
* Exit criteria: `drift-shift` scenario promotes a challenger without manual steps (S5).
* Must explain: PSI, why shadow before promote, why not auto-deploy every retrain.

## Phase 8: Polish (week 18)

* Benchmarks table filled, demo video, ADRs complete, blog post on the hardest bug.
* Final test: whiteboard the whole system from memory.
