# 01 Charter

## Problem

Card fraud is decided in the authorization window: the bank has roughly 100 ms to approve or decline before the terminal times out. A good system must be fast, accurate on extremely imbalanced data, explainable to analysts and regulators, and able to adapt, because fraudsters change tactics as soon as they get caught.

## Goals

1. **Real-time decisions.** Score every authorization synchronously with p99 under 50 ms.
2. **Better than rules.** Beat a hand-written rules engine on PR-AUC and on expected business cost.
3. **Explain every decision.** Return the top 3 reason codes with each decision.
4. **Close the loop.** Labels from analysts and late chargebacks flow back into training.
5. **Adapt safely.** Detect drift, retrain, shadow-test the challenger on live traffic, promote only if it wins.
6. **Fail predictably.** Every dependency failure has a documented, tested behaviour.

## Non-goals

* Real customer data. All data is synthetic; nothing here touches real payments or any employer system.
* Authentication, multi-tenancy, PCI compliance. Noted as out of scope, not ignored by accident.
* Kubernetes. Docker Compose is enough to prove the design; scaling notes live in the architecture doc.
* Deep learning. Tabular fraud is where gradient-boosted trees win (see ADR-0005).

## Success metrics (definition of done)

| # | Metric | Target | How it is measured |
|---|---|---|---|
| S1 | Scoring latency | p99 < 50 ms at 500 TPS | Prometheus histogram during `make bench` |
| S2 | Throughput | 1,000 TPS sustained for 10 min, zero lost or duplicated decisions | load test + row counts reconciled against sent count |
| S3 | Detection | PR-AUC and expected cost better than rules-only | `ml-platform evaluate` on time-based holdout |
| S4 | Explainability | 100% of decisions have >= 1 reason code | contract test |
| S5 | Drift response | injected shift detected and challenger promoted automatically | chaos scenario `drift-shift` |
| S6 | Reliability | every row in the failure-modes doc has a passing chaos test | `make chaos` |
| S7 | Reproducibility | fresh clone to running demo in under 10 minutes | someone else tries it |

## Learning objectives

This project exists to make its author a stronger engineer. By the end, without notes, I can:

* Whiteboard the system and trace one transaction from gateway to dashboard.
* Explain why the hot path is synchronous and the cold path is event-driven.
* Explain point-in-time correctness and training-serving skew, and how this codebase prevents both.
* Explain PR-AUC, precision, recall, and why accuracy is useless at a 1% fraud rate.
* Pick thresholds from a cost matrix and defend them.
* Explain idempotency, at-least-once delivery, and how duplicates are made harmless.
* Describe what happens when each dependency fails, and why that behaviour was chosen.
* Justify every row in the ADR folder.

## The 30-second pitch

"I built a real-time fraud detection system. A simulated payment gateway sends card authorizations to a FastAPI scoring service that computes live behavioural features from Redis, combines rules with a LightGBM model, and responds in under 50 ms at p99 with reason codes. Decisions stream through Kafka into Postgres and a live analyst dashboard. Labels come back from analysts and delayed chargebacks, and the system detects drift, retrains, shadow-tests the new model on live traffic, and promotes it only if it measurably beats the current one."
