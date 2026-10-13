"""Build the training table by replaying events through fraudcore (ADR-0006).

for each transaction in event_time order:
    state = states.get(card_id) or CardState(card_id)
    row = compute_features(txn, state)     # point-in-time correct by construction
    states[card_id] = update_state(txn, state)

There is no second implementation of any feature here: this file only loops.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Iterator
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from fraudcore.features import FEATURE_NAMES, CardState, compute_features, update_state
from fraudcore.schemas import Transaction

IDENTIFIER_COLUMNS = ["txn_id", "card_id", "event_time"]
# Ground truth from the simulator. The label is the only one a model may learn from; the
# rest is for analysis (per-pattern results) and must never be a feature.
LABEL_COLUMNS = ["is_fraud", "fraud_pattern", "attack_id"]


def replay_features(txns: Iterable[Transaction]) -> Iterator[dict[str, float]]:
    """Yield one feature dict per transaction, in the order given (event-time order).

    State is held per card in memory, exactly as Redis holds it online.
    """
    states: dict[str, CardState] = {}
    for txn in txns:
        state = states.get(txn.card_id) or CardState(txn.card_id)
        features = compute_features(txn, state)  # 1. the past only
        states[txn.card_id] = update_state(txn, state)  # 2. then absorb this transaction
        yield features


def build_feature_table(src: str | Path, dst: str | Path) -> int:
    """Read the simulator's Parquet, write identifiers + label columns + features. Returns rows."""
    table = pq.read_table(src)
    contract = list(Transaction.model_fields)
    records = table.select(contract).to_pylist()
    order = sorted(
        range(len(records)), key=lambda i: (records[i]["event_time"], records[i]["txn_id"])
    )

    txns = (Transaction.model_validate(records[i]) for i in order)
    feature_rows = list(replay_features(txns))

    def column(name: str) -> list:
        values = table.column(name).to_pylist()
        return [values[i] for i in order]

    data: dict[str, list] = {name: column(name) for name in IDENTIFIER_COLUMNS + LABEL_COLUMNS}
    for name in FEATURE_NAMES:
        data[name] = [row[name] for row in feature_rows]

    out = pa.table(data)
    meta = dict(table.schema.metadata or {})
    meta[b"feature_names"] = json.dumps(FEATURE_NAMES).encode()
    meta[b"source_rows"] = str(len(records)).encode()
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(out.replace_schema_metadata(meta), dst)
    return len(records)


def run(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(prog="mlp replay", description=__doc__.split("\n")[0])
    parser.add_argument("--in", dest="src", default="data/txns.parquet")
    parser.add_argument("--out", default="data/features.parquet")
    args = parser.parse_args(argv)
    rows = build_feature_table(args.src, args.out)
    print(f"replayed {rows:,} transactions into {args.out}")
