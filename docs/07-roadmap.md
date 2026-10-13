# 07 Roadmap

Each phase has a goal, user stories with acceptance criteria, requirements, tests, doc updates, exit criteria, and questions you must answer out loud without notes before moving on. Write a design note (`docs/design-notes/`) at the start of every phase.

## How to read this doc

* **Stories** say who needs what and why. **Acceptance criteria** (AC) say how we know a story is done.
* **Requirements** are the testable facts the code must satisfy. IDs look like `P2-R3` (phase 2, requirement 3). Reference them in tests and commit messages.
* **Traces** link a phase to the charter success metrics S1 to S7 (`docs/01-charter.md`).
* Checkboxes are for tracking. Tick one only when the AC is met and verified, not when the code is written.

## Working mode and ownership

* **Ownership column.** "You write" and "Claude can help" are the original designation of each file (see service READMEs and `CLAUDE.md`).
* **Current mode (author's decision, 2026-10-12).** Claude writes the code, including in "you write" files. After each piece Claude explains it line by line, and the author restates the key idea in their own words. The author must be able to explain every line.
* **Phase gate (changed 2026-10-12).** The author waived the must-explain sign-off and asked not to be quizzed. A phase is complete when its exit criteria are met, tests and lint pass, and docs are updated. The "must explain" lists stay as study material.
* **Definition of done for every story** (from `CLAUDE.md`): tests added or updated, `make test` and `make lint` pass, docs updated if behaviour/contracts/features/failure modes changed, any performance claim backed by a benchmark in `benchmarks/`, and a short explanation of what changed and why.

## Status

| Phase | Name | Weeks | Status | Traces |
|---|---|---|---|---|
| 0 | Foundations | 1 | Complete (2026-10-12) | S7 (start) |
| 1 | Synthetic world | 2 to 3 | Complete (2026-10-12) | S3 (data) |
| 2 | Offline model | 4 to 5 | In progress: features done, replay and models next | S3, S4 (partial) |
| 3 | Scoring service | 6 to 7 | Not started | S1, S4 |
| 4 | Real-time pipeline | 8 to 10 | Not started | S2 |
| 5 | Reliability | 11 to 12 | Not started | S1, S2, S6 |
| 6 | Analyst loop and dashboard | 13 to 14 | Not started | S4, demo |
| 7 | Adaptation | 15 to 17 | Not started | S5 |
| 8 | Polish | 18 | Not started | S7, all |

Dependencies are strictly sequential: each phase consumes the output of the one before it (Parquet from 1, features and model from 2, service from 3, and so on).

---

## Phase 0: Foundations (week 1)

**Goal.** A scaffold that runs end to end on the author's laptop, and an author who can explain the architecture.

**Deliverable.** `make up` starts infra; `make topics`, `make test` and `make lint` work; CI is green.

### Stories

* **P0-1** As the author, I want the repo under version control with a remote so my work is backed up and CI can run.
  * AC: `origin` points at GitHub; scaffold committed and pushed to `main`; `.idea/` and `.env` are not tracked.
* **P0-2** As the author, I want one command to start all infrastructure so I can run the system without remembering container details.
  * AC: `cp .env.example .env && make up` starts Redis, Redpanda and Postgres healthy; Redpanda console opens at `localhost:8080`.
* **P0-3** As the author, I want the Kafka topics created reproducibly so every environment has the same topics.
  * AC: `make topics` creates `transactions.scored` (6 partitions), `labels.chargeback` (3), `labels.analyst` (3) and `transactions.scored.dlq` (1), matching `docs/03-data-contracts.md`. Running it twice does not fail.
* **P0-4** As the author, I want tests and lint to run from one command so I get fast feedback.
  * AC: `make test` passes (unbuilt work is `xfail`, not failing); `make lint` passes; CI runs both on every push and is green.
* **P0-5** As the author, I want to understand the design before building it.
  * AC: every doc in `docs/` read; hot path vs cold path explained out loud without notes.

### Requirements

* **P0-R1** Setup from a fresh clone needs only Docker, Python 3.12 and the Makefile targets, with no undocumented manual steps.
* **P0-R2** No secrets are committed; configuration comes from environment variables (`.env.example` is the template).
* **P0-R3** Every test for unbuilt work is `xfail` and names the phase that removes the mark.

### Checklist

- [x] Git repo initialised, `origin` added, scaffold pushed to `main`
- [x] `make up` healthy (Docker running). Note: `event-sink` exits immediately until Phase 4 (its `main()` is a stub that raises `NotImplementedError`); this is expected.
- [x] `make topics` creates all four topics (safe to re-run)
- [x] `make test` and `make lint` pass locally
- [x] CI green on GitHub (commit `0323179`)
- [x] All docs read (author confirmed)
- [x] Hot vs cold path and features-before-state rule explained by the author

### Exit criteria

You can explain the architecture diagram and the hot vs cold path split.

### Must explain

Hot vs cold path and why the split exists (ADR-0002); why features are computed before state is updated.

### Risks

* Docker or port conflicts (8000, 8001, 8080, 9090, 3000, 3001). Mitigation: check ports before `make up`.

---

## Phase 1: Synthetic world (weeks 2 to 3)

**Goal.** A believable, labelled dataset: realistic normal customers plus four fraud patterns, with ground truth known.

**Deliverable.** `gateway-sim` writes realistic customers and 4 fraud patterns to a Parquet file (no network yet).

**Files.** You write: `customers.py`, `patterns.py`. Claude can help: CLI wiring, Parquet output.

### Stories

* **P1-1** As a model trainer, I want customers with distinct, stable habits (home city, favourite merchants, spend level, active hours, devices) so that "normal" has structure a model can learn deviations from.
  * AC: customer types are varied (for example students, families, travellers), mostly domestic; amounts are log-normal; activity is daytime-weighted; ecommerce transactions carry a `device_id` and card-present ones do not.
* **P1-2** As a model trainer, I want stolen-card-travel fraud so the system can learn impossible travel.
  * AC: a card used in one city, then far away within a time that implies speed beyond plausible travel.
* **P1-3** As a model trainer, I want card-testing fraud so the system can learn burst behaviour.
  * AC: many small transactions on one card in a short window, mostly declined-style probes, then possibly one larger purchase.
* **P1-4** As a model trainer, I want account-takeover fraud so the system can learn new-device and unusual-spend signals.
  * AC: a known card suddenly used from a new device with higher-than-usual amounts and unfamiliar merchants.
* **P1-5** As a model trainer, I want merchant-compromise fraud so the system can learn from many cards hitting one merchant.
  * AC: a burst of fraud across many different cards sharing a merchant within a time window.
* **P1-6** As the author, I want every event to carry ground truth (`is_fraud`, pattern name) in a separate column so training labels are exact and never leak into features.
  * AC: ground truth is written to the Parquet file but is not part of the `Transaction` contract.
* **P1-7** As the author, I want a repeatable run so experiments are comparable.
  * AC: the CLI takes a seed, population size and duration; the same seed gives byte-identical output.

### Requirements

* **P1-R1** Fraud rate is about 1% overall (model card target is 0.5 to 1%); each of the four patterns appears in meaningful numbers.
* **P1-R2** All output validates against `fraudcore.schemas.Transaction`; amounts are integer cents (ADR-0007); times are UTC `event_time`.
* **P1-R3** Events are ordered by `event_time` in the file, and the simulator runs on event time, not wall-clock time.
* **P1-R4** Synthetic data only: no real card data, nothing from the author's employer.
* **P1-R5** Normal behaviour must overlap fraud somewhat (for example legitimate travellers, legitimate big purchases) so the data is not trivially separable.
* **P1-R6** Record the generator version with the output so each trained model can reference it (model card requirement).

### Tests

* Seeded run is deterministic.
* Output rows pass schema validation; no float amounts.
* Observed fraud rate is within the target band.
* Per-pattern unit tests: each generator produces the signal it claims (for example speed above a threshold for stolen-card travel).

### Docs

* Fill in `docs/design-notes/phase-1-synthetic-world.md` before coding: normal customer, each pattern's signal and traffic share, how the data could be unrealistically easy, how we will know it works.
* Update `docs/05-model-card.md` Data section with the generator version.

### Exit criteria

* [x] Fraud rate about 1% (measured 1.00% on the default run).
* [x] A plot of normal vs fraud spending looks plausible: `docs/images/phase1-spending.png` shows amount and hour of day. The distance-from-home plot waits for Phase 2, because distance is feature logic and belongs in `fraudcore/features/geo.py` (invariant 1).
* [x] Stories P1-1 to P1-7 built and tested (merchants, customers, four patterns, ground truth, seeded CLI). Results and the "still too easy on amount" finding are in the design note.
* [x] Must-explain sign-off: waived by the author (2026-10-12); the questions below are study material.

### Must explain

What makes each pattern detectable; why realistic normal behaviour matters as much as the fraud.

### Risks

* Data too easy (a model scoring 0.99 PR-AUC means the generator leaks the answer). Mitigation: R5 overlap and a sanity check in Phase 2.
* Patterns tuned to the features you plan to build (circular reasoning). Mitigation: define patterns from fraud behaviour, then see which features catch them.

---

## Phase 2: Offline model (weeks 4 to 5)

**Goal.** Prove a model beats rules, using the same feature code the live service will use.

**Deliverable.** `ml-platform replay`, `train`, `evaluate` produce the model-card results table.

**Files.** You write: `features/compute.py`, `features/geo.py`, `replay.py`, `evaluate.py`, threshold selection from the cost matrix. Claude can help: plotting, LightGBM boilerplate.

### Stories

* **P2-1** As the author, I want pure feature functions so the same code serves training and serving (ADR-0006).
  * AC: `compute_features(txn, state)` returns the full feature set from `docs/04-feature-catalog.md` with no I/O; `update_state(txn, state)` returns the new state; windows are pruned and device/merchant sets are capped.
* **P2-2** As the author, I want a correct haversine distance so impossible-travel features are right.
  * AC: Toronto (43.65, -79.38) to Calgary (51.05, -114.07) is about 2,700 km, within tolerance.
* **P2-3** As the author, I want to replay historical events through the feature code in event-time order so training data matches what serving would have produced.
  * AC: `replay` reads the Phase 1 Parquet, runs compute then update per event in order, and writes a feature table with labels.
* **P2-4** As the author, I want baselines so I can prove the model is worth it.
  * AC: a rules-only baseline and a logistic regression are evaluated on the same splits as LightGBM.
* **P2-5** As the author, I want a time-based split so metrics reflect the future, not leakage.
  * AC: train, validation and test are consecutive time windows; no random splitting anywhere.
* **P2-6** As the author, I want thresholds chosen from business cost, not guesses.
  * AC: `review_threshold` and `decline_threshold` minimise expected cost on validation using the cost matrix in `docs/05-model-card.md`; results are then reported on test; the cost curve is plotted.

### Requirements

* **P2-R1** Point-in-time correctness: a transaction's features use only events strictly before its `event_time` (invariant 2, catalog rule 1).
* **P2-R2** Cold start: a card with empty state yields defined values for every feature, and training data includes cold-start rows.
* **P2-R3** Out-of-order events do not move `last_*` fields backwards (F8).
* **P2-R4** Money is integer cents in every feature that uses amounts (invariant 4).
* **P2-R5** Headline metric is PR-AUC; precision, recall and expected cost per 1,000 transactions are reported; accuracy is never a headline number.
* **P2-R6** Calibration is checked, because scores are used as probabilities in the cost math.
* **P2-R7** Every feature has a catalog row and a point-in-time unit test; an ablation (with vs without the feature) is noted in the model card.
* **P2-R8** No feature, notebook or script computes features outside `libs/fraudcore/fraudcore/features/` (invariant 1).

### Tests

* Unit: one test per windowed feature at the boundary (event exactly at the window edge), cold start, out-of-order, haversine.
* Unit: replay of a tiny hand-built sequence matches hand-computed features.
* Metric sanity: LightGBM PR-AUC well above the fraud-rate baseline and above rules; suspiciously perfect scores trigger a leakage investigation.

### Docs

* Update `docs/04-feature-catalog.md` for any new feature; fill the results table and thresholds in `docs/05-model-card.md`.

### Exit criteria

LightGBM beats rules on PR-AUC and expected cost; time-based split; feature unit tests pass.

### Must explain

PR-AUC vs ROC-AUC; why a time split; point-in-time correctness; how thresholds came from costs.

### Risks

* Leakage through features that use the label or post-decision information (catalog rule 4). Mitigation: review each feature against the rule before merging.
* Cost-matrix assumptions drive the thresholds. Mitigation: state them in the model card and show sensitivity.

---

## Phase 3: Scoring service (weeks 6 to 7)

**Goal.** A FastAPI service that scores one transaction and returns a decision with reasons, inside the latency budget, with state still in memory or a stub.

**Deliverable.** `POST /v1/score` returns decisions with reasons; latency histogram exported.

**Files.** You write: `pipeline.py`, `rules.py`, `decision.py`, reason-code mapping. Claude can help: FastAPI app wiring, Prometheus setup, Dockerfile.

### Stories

* **P3-1** As the gateway, I want one synchronous endpoint that returns APPROVE, REVIEW or DECLINE so I can answer the terminal in time.
  * AC: `POST /v1/score` validates a `Transaction` and returns a `Decision` per `docs/03-data-contracts.md`.
* **P3-2** As an analyst, I want every decision to carry its top reasons so I can understand it.
  * AC: top 3 positive TreeSHAP contributions (`pred_contrib=True`) are mapped to reason codes in `fraudcore/reasons.py`; every decision has at least one reason (S4).
* **P3-3** As the business, I want hard rules alongside the model so known-bad patterns are caught regardless of the score.
  * AC: rules such as CARD_TESTING and HIGH_RISK_NEW_DEVICE can fire; `rules_fired` lists them; a fired rule can only make the action stricter, never looser.
* **P3-4** As the author, I want latency measured so performance claims are real.
  * AC: a Prometheus histogram exports scoring latency; p50 and p99 are recorded in `benchmarks/results/` with the load-test command used.
* **P3-5** As an operator, I want health and readiness endpoints so I know when the service can serve.
  * AC: `/ready` is false when no champion model is loaded (F4).

### Requirements

* **P3-R1** Order of operations in the pipeline: idempotency check, load state, `compute_features`, rules, champion score and contributions, challenger shadow score, thresholds and reasons, `update_state`, save state and decision, publish (non-blocking). Features always before state update (invariant 2).
* **P3-R2** The hot path never touches Postgres and never awaits Kafka delivery (invariant 3).
* **P3-R3** Latency budget (from `docs/02-architecture.md`): total budgeted 18.5 ms at p99 against a 50 ms target; update the table with measured numbers if it is blown.
* **P3-R4** The challenger score is logged only and never acted on (`shadow_score`, `shadow_model_version`).
* **P3-R5** Contract tests: response validates against the `Decision` schema; `model_version` and `decided_at` always set.
* **P3-R6** Thresholds come from the model card (Phase 2), not hard-coded literals scattered in code.

### Tests

* Contract test for request and response.
* Unit tests for decision logic: thresholds give a base action, rules only tighten it.
* Reason mapping test: known feature contributions map to the expected codes.
* Latency benchmark with Locust (`make bench`); results committed under `benchmarks/results/`.

### Docs

* Update the latency table in `docs/02-architecture.md` with measured values; add reason codes to the glossary if new.

### Exit criteria

p99 measured and recorded; contract tests pass.

### Must explain

p50 vs p99; where every millisecond goes; why contributions come from TreeSHAP.

### Risks

* Challenger scoring pushes p99 over budget. Mitigation: it is skippable under load shedding (F9).
* Python overhead in feature computation. Mitigation: measure before optimising.

---

## Phase 4: Real-time pipeline (weeks 8 to 10)

**Goal.** Real state, real events, no duplicates, no losses: Redis for state and idempotency, Kafka for the event log, Postgres as the system of record.

**Deliverable.** State in Redis, idempotency, decisions published to Kafka, sink writes Postgres, simulator streams live.

**Files.** You write: `stores/redis_state.py`, idempotency, event-sink consumer logic, parity test. Claude can help: compose config, topic scripts, aiokafka boilerplate.

### Stories

* **P4-1** As the scoring service, I want per-card state in Redis so velocity features survive restarts and scale across replicas.
  * AC: `card:{card_id}:state` stores serialized `CardState` with a 30-day TTL; a missing key yields empty `CardState`.
* **P4-2** As the gateway, I want a retry to return the original decision so duplicates are harmless (F5).
  * AC: `idem:{txn_id}` is set with NX; a repeated `txn_id` returns the stored decision (24 h TTL) and does not touch state.
* **P4-3** As the cold path, I want every decision published to `transactions.scored` keyed by `card_id` so per-card ordering holds.
  * AC: producer uses `acks=all`, idempotence on, small `linger_ms`; the call is fire-and-forget on the hot path.
* **P4-4** As the system of record, I want the sink to write events to Postgres idempotently so replays are safe (F6).
  * AC: upserts are `ON CONFLICT (txn_id) DO NOTHING` (labels keyed by `txn_id, source`); replaying a topic twice leaves Postgres unchanged.
* **P4-5** As an operator, I want poison messages isolated so one bad event cannot block a partition (F7).
  * AC: deserialization errors go to `transactions.scored.dlq`, the offset is committed, and an alert/log is emitted.
* **P4-6** As the author, I want proof that online and offline features are identical so training-serving skew cannot creep in.
  * AC: the parity test in `tests/contract/` feeds the same event sequence through the online path and the replay path and asserts identical feature vectors.
* **P4-7** As the author, I want the simulator to stream live and to retry with the same `txn_id` sometimes so idempotency is exercised.
  * AC: `gateway-sim` live mode uses `httpx.AsyncClient`, rate-controlled, with deliberate retries.
* **P4-8** As the author, I want to settle the open question: should declined attempts update velocity state?
  * AC: decision recorded in a design note or ADR with reasoning (card-testing attacks are mostly declines).

### Requirements

* **P4-R1** All consumers and writes are idempotent; delivery is at-least-once (invariant 5).
* **P4-R2** Keys are `card_id` for topics; Redis keys use the `{card_id}` hash tag so a card's keys live on one shard.
* **P4-R3** Out-of-order events for a card do not move `last_*` backwards (F8), and state is bounded (pruned windows, capped sets).
* **P4-R4** `/ready` also checks Redis.
* **P4-R5** No loss and no duplicates: decisions sent equals decisions stored, reconciled by row count after a run.
* **P4-R6** The hot path still never awaits Kafka delivery (invariant 3).

### Tests

* Integration: duplicate request returns identical decision and state is unchanged.
* Integration: replaying the topic twice leaves Postgres row counts and contents unchanged.
* Integration: poison message lands in DLQ and the partition keeps flowing.
* Contract: parity test (online vs offline) green; remove the `xfail`.

### Docs

* Update `docs/03-data-contracts.md` if contracts change; record the velocity-on-decline decision; update the runbook if commands change.

### Exit criteria

Parity test green; replaying a topic twice leaves Postgres unchanged.

### Must explain

Training-serving skew; at-least-once delivery; why keys are `card_id`; idempotency end to end.

### Risks

* State races when two requests for the same card overlap (F10), deferred to Phase 5. Mitigation: document the known gap.
* Serialization drift between online and offline state. Mitigation: parity test.

---

## Phase 5: Reliability (weeks 11 to 12)

**Goal.** Every failure in `docs/06-failure-modes.md` has implemented behaviour and a test that proves it.

**Deliverable.** Every row in doc 06 has behaviour implemented and a chaos test.

**Files.** You write: circuit breaker, fallback mode, concurrency control (F10), ADR-0008 final decision.

### Stories

* **P5-1** As the gateway, I want decisions even if Redis is down or slow (F1).
  * AC: calls over about 5 ms trip a circuit breaker; the service falls back to stateless rules with the ADR-0008 policy (proposed: fail open under $100, REVIEW above); recovery closes the breaker.
* **P5-2** As the gateway, I want decisions even if Kafka is down (F2).
  * AC: events buffer in memory to a bound, then are dropped and counted; decisions never wait.
* **P5-3** As the cold path, I want the sink to pause cleanly if Postgres is down and catch up afterwards (F3).
  * AC: no loss and no duplicates after a 30 s outage; lag grows then drains.
* **P5-4** As an operator, I want a bad model file never to be served (F4).
  * AC: a missing or corrupt model on reload keeps the previous model; with none, rules-only and `/ready` false.
* **P5-5** As the author, I want concurrent requests for the same card handled correctly (F10).
  * AC: a decision between optimistic locking (WATCH/MULTI), Lua scripts, or per-card routing, recorded in an ADR, with a concurrency test showing no lost updates.
* **P5-6** As the author, I want overload to degrade gracefully (F9).
  * AC: challenger shadow scoring is shed first, then 503 for gateway retry.
* **P5-7** As the author, I want the load test to prove the headline numbers.
  * AC: `make bench` demonstrates S1 (p99 under 50 ms at 500 TPS) and S2 (1,000 TPS sustained for 10 minutes, zero lost or duplicated decisions).

### Requirements

* **P5-R1** Each failure mode F1 to F11 has: detection, defined behaviour, and a passing test (unit, integration, or chaos).
* **P5-R2** ADR-0008 (fail open vs fail closed) is finalised with the reasoning and the dollar threshold justified.
* **P5-R3** After every chaos run, check decisions sent vs stored, p99 during the incident, and recovery time (runbook).
* **P5-R4** Reliability behaviour is observable: metrics for breaker state, dropped events, shed requests, DLQ counts.

### Tests

* `make chaos` (redis, kafka, postgres) is green.
* Concurrency test for F10; unit tests for F4 and F8; load test for F9.

### Docs

* Update `docs/06-failure-modes.md` with final behaviours; finalise ADR-0008; add the F10 ADR; update the runbook.

### Exit criteria

`make chaos` green; load test hits S1 and S2.

### Must explain

Every failure mode and why that behaviour.

### Risks

* Fail-open policy is a business tradeoff, not a technical one. Mitigation: state the cost reasoning in ADR-0008.
* Laptop-bound benchmarks vary run to run. Mitigation: record the environment and repeat runs.

---

## Phase 6: Analyst loop and dashboard (weeks 13 to 14)

**Goal.** Close the human loop: see decisions live, trigger attacks, review flagged cases, and emit labels.

**Deliverable.** Live feed, attack buttons, threshold sliders, review queue that emits labels.

**Files.** You write: review-queue logic and label flow in `analyst-api`. Claude can help: most of the React UI.

### Stories

* **P6-1** As an analyst, I want a live feed of scored transactions so I can watch traffic.
  * AC: the analyst API consumes `transactions.scored` with its own consumer group and pushes to clients over WebSocket.
* **P6-2** As an analyst, I want a review queue of REVIEW decisions with features and reasons so I can judge each case.
  * AC: oldest unreviewed first; each item shows score, reasons, key features.
* **P6-3** As an analyst, I want to label a case fraud or legit and have it flow back into the system.
  * AC: submitting a label publishes a `Label(source=analyst)` to `labels.analyst` and marks the item reviewed; the sink writes it to Postgres idempotently.
* **P6-4** As a demo presenter, I want attack buttons so I can inject fraud on demand.
  * AC: the dashboard calls analyst-api, which forwards to the gateway-sim control API.
* **P6-5** As a risk manager, I want threshold sliders so I can see how the action mix and cost change.
  * AC: moving a slider shows estimated review volume and cost; applying it is a deliberate action.
* **P6-6** As the author, I want a metrics view showing p99, PR-AUC and cost vs the rules baseline.
  * AC: values come from real benchmark/eval outputs, not placeholders.

### Requirements

* **P6-R1** Analyst labels exist only for REVIEW cases, so they are a biased sample; never evaluate on analyst labels alone (architecture doc section 6).
* **P6-R2** Label writes are idempotent (`txn_id, source`).
* **P6-R3** The live-feed consumer uses its own group and reads from the latest offset so it does not disturb other consumers.
* **P6-R4** UI is read/act only; no business logic or feature code in the dashboard (invariant 1).

### Tests

* Unit/integration: queue ordering, label publish and idempotent write.
* End to end: the 3-minute demo in the runbook runs without manual patching.

### Docs

* Update the runbook demo steps if the UI differs; update data contracts if label fields change.

### Exit criteria

The 3-minute demo in the runbook works end to end.

### Must explain

Why analyst labels are biased; how a label gets from the UI to Postgres; why labels arrive late and how training handles that.

### Risks

* Time sink in UI polish. Mitigation: Claude builds most of the React UI; keep the author's focus on the review-queue and label logic.

---

## Phase 7: Adaptation (weeks 15 to 17)

**Goal.** The system notices that fraud has changed and safely replaces its own model.

**Deliverable.** Adversarial attacker, PSI drift detection, Isolation Forest, automated retrain, shadow, promote.

**Files.** You write: `drift.py`, `promote.py` gates, shadow comparison.

### Stories

* **P7-1** As the author, I want an adaptive attacker that changes tactics when caught so the system has something real to adapt to.
  * AC: the attacker shifts a pattern parameter (for example amounts, timing, merchants) after detection drops.
* **P7-2** As the system, I want to detect distribution shift automatically.
  * AC: PSI per feature and on the score distribution, live window vs training window; PSI > 0.2 raises a drift alert. Bins come from the expected (training) quantiles, with a small epsilon to avoid log(0).
* **P7-3** As the system, I want an unsupervised model so unseen patterns can still raise a flag.
  * AC: Isolation Forest is trained and its score is available as a signal and evaluated in the model card.
* **P7-4** As the system, I want to retrain on matured labels when drift is detected.
  * AC: a retrain job uses only transactions whose label window has closed, with a time-based split.
* **P7-5** As the system, I want the challenger to score live traffic in shadow so it is compared on the real thing.
  * AC: challenger score is logged next to the champion's for the same transactions and never acted on.
* **P7-6** As the system, I want to promote only when gates pass.
  * AC: `promote.py` enforces the model-card gates; promotion is an atomic pointer swap in the registry; scoring reloads without restarting and keeps the old model if the new load fails (F4).
* **P7-7** As the author, I want the whole loop proven by one scenario.
  * AC: the `drift-shift` scenario promotes a challenger with no manual steps (S5); time to detect is recorded in the README benchmarks.

### Requirements

* **P7-R1** Promotion gates (model card): offline PR-AUC at least the champion's and expected cost lower on the latest holdout; shadow scored at least N hours or N thousand live transactions; on matured labels, recall not worse by more than 1 point at equal review rate; challenger p99 within budget.
* **P7-R2** Not every retrain is auto-deployed; a retrain only becomes champion by passing gates.
* **P7-R3** Training sets exclude transactions whose label window has not closed; unlabelled-after-window is treated as legit and the bias is documented.
* **P7-R4** Model reload is atomic and never serves a partially loaded model.

### Tests

* Unit: PSI on known distributions (identical gives about 0; a clear shift gives above 0.2).
* Unit: each promotion gate passes and fails on constructed inputs.
* Scenario: `drift-shift` end to end (S5).

### Docs

* Fill the Monitoring and Promotion sections and limitations in `docs/05-model-card.md`; ADR for the promotion policy if it differs from the model card.

### Exit criteria

`drift-shift` scenario promotes a challenger without manual steps (S5).

### Must explain

PSI; why shadow before promote; why not auto-deploy every retrain.

### Risks

* Feedback loop and selection bias: the model only sees labels for cases it flagged or that charge back. Mitigation: document it; compare on matured labels.
* A flaky drift threshold causes promotion churn. Mitigation: gates plus a minimum shadow volume.

---

## Phase 8: Polish (week 18)

**Goal.** Make the project demonstrable, reproducible and defensible.

### Stories

* **P8-1** As a reviewer, I want the benchmarks table filled with real, reproducible numbers.
  * AC: every README benchmark row links to the script that produced it in `benchmarks/`.
* **P8-2** As a reviewer, I want a demo video of the 3-minute runbook demo.
* **P8-3** As a reviewer, I want complete ADRs so every decision has a recorded reason (charter learning objective).
* **P8-4** As the author, I want a blog post on the hardest bug to cement what I learned.
* **P8-5** As someone cloning the repo, I want fresh clone to running demo in under 10 minutes (S7).
  * AC: someone else tries it and succeeds, following only the README.

### Requirements

* **P8-R1** All of S1 to S7 are met and backed by numbers in the README.
* **P8-R2** No `xfail` marks remain, and none were removed before the phase's exit criteria were met.
* **P8-R3** Docs match behaviour: contracts, feature catalog, model card results, failure modes, runbook.

### Exit criteria

Benchmarks table filled, demo video, ADRs complete, blog post on the hardest bug.

### Final test

Whiteboard the whole system from memory.

---

## Traceability: charter metrics to phases

| Metric | Target | Built in | Proven in |
|---|---|---|---|
| S1 Latency | p99 < 50 ms at 500 TPS | Phase 3 | Phase 5 (`make bench`) |
| S2 Throughput | 1,000 TPS for 10 min, no loss or duplicates | Phase 4 | Phase 5 |
| S3 Detection | beats rules on PR-AUC and expected cost | Phase 2 | Phase 2, re-checked in Phase 7 |
| S4 Explainability | every decision has at least 1 reason code | Phase 3 | Phase 3 contract test |
| S5 Drift response | detect, retrain, shadow, promote automatically | Phase 7 | `drift-shift` scenario |
| S6 Reliability | every failure mode has a passing chaos test | Phase 5 | `make chaos` |
| S7 Reproducibility | fresh clone to demo in under 10 minutes | Phase 0 onward | Phase 8 |

## Open questions to settle

| Question | Settle in | Recorded as |
|---|---|---|
| Should declined attempts update velocity state? | Phase 4 | design note or ADR |
| Concurrency control for same-card requests (WATCH, Lua, or routing) | Phase 5 | ADR |
| Fail-open threshold under Redis failure | Phase 5 | ADR-0008 final |
| Split hot Redis fields into sorted sets/hashes? | Phase 5, only if profiling says so | ADR |
| Promotion thresholds (N hours or N thousand live txns) | Phase 7 | model card |
