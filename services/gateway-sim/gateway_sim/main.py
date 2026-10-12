"""Simulator entrypoint.

Phase 1: python -m gateway_sim.main --offline --days 30 --out data/txns.parquet
Phase 4: python -m gateway_sim.main --rate 200   (live, posts to scoring)
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date

from gateway_sim.customers import generate_population
from gateway_sim.merchants import Catalog
from gateway_sim.output import write_parquet
from gateway_sim.simulate import GENERATOR_VERSION, simulate


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="gateway_sim", description="Synthetic card transactions.")
    p.add_argument("--offline", action="store_true", help="write a Parquet file, no network")
    p.add_argument("--customers", type=int, default=1_000)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--start", default="2026-01-01", help="first day, YYYY-MM-DD")
    p.add_argument("--seed", type=int, default=42, help="same seed gives the same file")
    p.add_argument("--fraud-rate", type=float, default=0.01, help="share of fraud transactions")
    p.add_argument("--out", default="data/txns.parquet")
    return p


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    # TODO(phase 4): live mode with httpx.AsyncClient, retries with SAME txn_id (tests idempotency),
    #                delayed chargeback labels published to labels.chargeback
    if not args.offline:
        raise SystemExit("live mode arrives in Phase 4; run with --offline for now")
    if not 0 <= args.fraud_rate < 0.5:
        raise SystemExit("--fraud-rate must be at least 0 and below 0.5")

    start = date.fromisoformat(args.start)
    catalog = Catalog(args.seed)
    customers = generate_population(args.customers, args.seed, catalog, start, args.days)
    rows = simulate(
        customers,
        catalog,
        start=start,
        days=args.days,
        seed=args.seed,
        fraud_rate=args.fraud_rate,
    )
    meta = {
        "generator_version": GENERATOR_VERSION,
        "seed": str(args.seed),
        "customers": str(args.customers),
        "days": str(args.days),
        "start": args.start,
        "fraud_rate": str(args.fraud_rate),
    }
    write_parquet(rows, args.out, meta)

    fraud = [r for r in rows if r.is_fraud]
    cases = Counter(r.fraud_pattern for r in {r.attack_id: r for r in fraud}.values())
    txns = Counter(r.fraud_pattern for r in fraud)
    print(f"wrote {len(rows):,} transactions to {args.out} (generator {GENERATOR_VERSION})")
    print(f"fraud: {len(fraud):,} ({len(fraud) / len(rows):.2%})")
    for name in sorted(txns):
        print(f"  {name:<22} {cases[name]:>5} attacks {txns[name]:>6} transactions")


if __name__ == "__main__":
    main()
