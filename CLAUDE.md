# CLAUDE.md

Instructions for AI coding agents working in this repo. Read this first, every session.

## What this is

A real-time card fraud detection system, built as a learning project. The author's goal is to understand every line, not just to ship. Treat that as the top requirement.

## Read before doing anything

1. `docs/07-roadmap.md`: find the current phase (see "Current status" below)
2. `docs/02-architecture.md`: hot path vs cold path, ordering rules, latency budget
3. `docs/03-data-contracts.md` and `libs/fraudcore/fraudcore/schemas.py`
4. The ADRs in `docs/adr/` relevant to the files you will touch

## Current status

Phase: 0 (scaffolding). Update this line when a phase is completed.

## Learning mode: ownership rules (most important section)

Each service README marks files as **you write** (the author) or **Claude can help**.

* **"you write" files:** do NOT write the implementation. Instead explain concepts, ask guiding questions, review the author's code, point out bugs and edge cases, and suggest tests. Short illustrative snippets of a different example are fine; the solution itself is not.
* **"Claude can help" files:** implement freely, then explain what you wrote and why, so the author can follow every line.
* If the author explicitly says "write it for me" in a "you write" file, do it, but explain it line by line afterwards and ask them to restate the key idea.
* Never mark a phase complete or delete `xfail` marks without the author confirming they can answer that phase's "must explain" questions.

## Architecture invariants (never break these)

1. Feature logic lives ONLY in `libs/fraudcore/fraudcore/features/` as pure functions (ADR-0006). No feature code in services or notebooks.
2. `compute_features(txn, state)` runs BEFORE `update_state(txn, state)`. Always.
3. The scoring hot path never touches Postgres and never awaits Kafka delivery (ADR-0002).
4. Money is integer cents (ADR-0007). No floats for amounts anywhere.
5. All consumers and writes are idempotent; assume at-least-once delivery.
6. Train/validate/test splits are time-based, never random.
7. Every new feature gets a row in `docs/04-feature-catalog.md` and a point-in-time unit test.

## Commands

```bash
make up / make down / make nuke
make topics          # first run
make sim RATE=200
make test            # pytest
make lint            # ruff
make bench           # load test
make chaos           # failure scenarios
```

## Conventions

* Python 3.12, type hints everywhere, ruff for lint and format, line length 100.
* Pydantic models in `fraudcore.schemas` are the contracts; do not redefine them elsewhere.
* Tests for unbuilt work are `xfail` with the phase that removes the mark.
* Significant decisions get an ADR (`docs/adr/0000-template.md`). Do not edit accepted ADRs; supersede them.

## Definition of done for any change

* Tests added or updated, `make test` and `make lint` pass
* Docs updated if behaviour, contracts, features, or failure modes changed
* Any performance claim backed by a benchmark in `benchmarks/`
* A short explanation to the author of what changed and why

## Do not

* Use real card data or anything from the author's employer. Synthetic data only.
* Add dependencies without saying why.
* Over-engineer: no Kubernetes, no auth, no extra services beyond the architecture doc.
