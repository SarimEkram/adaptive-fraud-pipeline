"""Kafka to Postgres. At-least-once in, idempotent writes out (failure modes F3, F6, F7)."""

from __future__ import annotations

TOPICS = ["transactions.scored", "labels.chargeback", "labels.analyst"]
GROUP_ID = "event-sink"


def main() -> None:
    """TODO(phase 4), you write:

    * consume in batches, auto-commit OFF
    * validate with fraudcore schemas; failures go to transactions.scored.dlq (F7)
    * upsert in one DB transaction per batch (ON CONFLICT DO NOTHING)
    * commit offsets only AFTER the DB commit. Why that order? Write it in a design note.
    * REVIEW decisions also insert into review_queue
    """
    raise NotImplementedError


if __name__ == "__main__":
    main()
