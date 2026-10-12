# CLAUDE.md

Instructions for AI coding agents working in this repo. Read this first, every session.

## What this is

A real-time card fraud detection system, built as a learning project. The author's goal is to understand every line, not just to ship. Treat that as the top requirement.

## Read before doing anything

1. `docs/07-roadmap.md`: find the current phase (see "Current status" below), its stories (`P<phase>-<n>`) and requirements (`P<phase>-R<n>`)
2. `docs/02-architecture.md`: hot path vs cold path, ordering rules, latency budget
3. `docs/03-data-contracts.md` and `libs/fraudcore/fraudcore/schemas.py`
4. The ADRs in `docs/adr/` relevant to the files you will touch

## Current status

Phase: 2 (offline model), not started. Phases 0 and 1 completed 2026-10-12 (must-explain sign-off waived by the author). Update this line when a phase is completed.

## Learning mode: ownership rules (most important section)

Each service README marks files as **you write** (the author) or **Claude can help**. Those labels are the original designation and are kept for reference.

**Current working mode (author's decision, 2026-10-12): Claude writes all the code, including in "you write" files. The author must understand every line.** This applies to all phases until the author changes it.

**Working style (author's decision, 2026-10-12): do not ask the author questions.** No quizzes, no restate-the-idea prompts, no "which do you prefer" menus. Decide yourself, and list every decision you made under a "Decisions I made" heading in your summary so the author can veto any of them. Step 2 below and the "Understanding checks" section are suspended until the author turns them back on. Line-by-line explanations still happen. Never ask the author to explain, restate or confirm understanding of anything (told to me on 2026-10-12). That waives the old sign-off gate: a phase is complete when its exit criteria are met, tests and lint pass, and docs are updated. Record in the roadmap that the must-explain sign-off was waived by the author, and keep the "must explain" lists as study material only.

For every piece of code you write, in any file:

1. **Explain it line by line** afterwards, in plain language, with short analogies. Assume the author is new to Kafka, Redis, FastAPI and the ML side; define terms the first time they appear.
2. **Ask the author to restate the key idea** in their own words. If the restatement is wrong or vague, correct it gently and ask again. For core files, also run the stronger check in "Understanding checks" below.
3. **Point to the roadmap:** name the story and requirement IDs (for example `P2-1`, `P2-R1` in `docs/07-roadmap.md`) the code satisfies.
4. **Do not move on in silence:** if you wrote a lot, pause after each file or logical chunk so the author can digest it.

Phase gate:

* Do not mark a phase complete or delete `xfail` marks until the phase's exit criteria are met and tests pass. (The author waived the must-explain sign-off on 2026-10-12; do not ask for it.)
* Write the phase's design note (`docs/design-notes/`) with the author at the start of each phase. Claude drafts it from the author's answers to guiding questions; the author edits it until it says what they actually mean.
* Do not start a new phase's work until the author says to.

If the author later asks to write a file themselves, switch that file back to the original rule: explain concepts, ask guiding questions, review, point out bugs and edge cases, suggest tests, and do not write the solution.

### Understanding checks (core files only)

The restate-the-idea check in step 2 can be passed with a vague answer ("yeah, it computes the velocity"). For the core files, use a stronger check so "I read it" becomes "I can change it".

Core files: `compute.py`, `update_state`, `replay.py`, `evaluate.py` threshold selection, `pipeline.py`, idempotency, and the event-sink commit logic. Boring files (wiring, boilerplate, plots) keep the lighter check only.

After walking through the code, ask the author at least two of:

* a. "What breaks if I delete or reorder this line?"
* b. "What input would make this return a wrong answer?"
* c. A small variation to implement from scratch without looking at the original (for example: change the window to 5 minutes, or add one feature).

Do not move to the next file until the author answers correctly. A wrong or vague answer means explain again and re-ask with a different question, not move on.

## Known gaps (resolve in the design note before coding)

From the roadmap review. Do not walk into these; settle each in the phase's design note first.

* **Phase 4, idempotency race:** if a retry arrives after `SET NX` succeeds but before the decision is stored, define what it returns (wait briefly, or "processing" plus retry).
* **Phase 4, velocity policy:** settle P4-8 (do declined attempts update velocity state?) BEFORE writing the parity test. Offline replay must apply the same policy.
* **Phase 5, targets:** S1 (p99 < 50 ms) is the firm target. S2 (1,000 TPS sustained) likely needs multiple workers and is a stretch.
* **Phase 6, missing file:** `services/gateway-sim/gateway_sim/control.py` does not exist yet (the README lists it); create it then.

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
* A short explanation to the author of what changed and why, including the line-by-line walkthrough and restate-the-idea check from the learning mode section
* Story and requirement IDs from `docs/07-roadmap.md` referenced in tests and commit messages

## Do not

* Use real card data or anything from the author's employer. Synthetic data only.
* Add dependencies without saying why.
* Over-engineer: no Kubernetes, no auth, no extra services beyond the architecture doc.
