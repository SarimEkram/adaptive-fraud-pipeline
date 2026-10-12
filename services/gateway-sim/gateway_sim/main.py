"""Simulator entrypoint.

Phase 1: python -m gateway_sim.main --offline --days 30 --out data/txns.parquet
Phase 4: python -m gateway_sim.main --rate 200   (live, posts to scoring)
"""

from __future__ import annotations


def main() -> None:
    # TODO(phase 1): argparse, population, event-time loop, ground truth, parquet output
    # TODO(phase 4): live mode with httpx.AsyncClient, retries with SAME txn_id (tests idempotency),
    #                delayed chargeback labels published to labels.chargeback
    raise NotImplementedError


if __name__ == "__main__":
    main()
