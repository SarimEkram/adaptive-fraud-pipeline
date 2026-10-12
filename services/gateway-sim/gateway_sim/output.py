"""Parquet output. Contract columns first, then ground-truth columns."""

from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from gateway_sim.simulate import LabelledTxn

SCHEMA = pa.schema(
    [
        # The Transaction contract (docs/03-data-contracts.md).
        ("schema_version", pa.int32()),
        ("txn_id", pa.string()),
        ("card_id", pa.string()),
        ("customer_id", pa.string()),
        ("amount_cents", pa.int64()),  # ADR-0007: integer cents, never float
        ("currency", pa.string()),
        ("merchant_id", pa.string()),
        ("mcc", pa.string()),
        ("merchant_country", pa.string()),
        ("lat", pa.float64()),
        ("lon", pa.float64()),
        ("channel", pa.string()),
        ("device_id", pa.string()),
        ("event_time", pa.timestamp("us", tz="UTC")),
        # Ground truth. Never an input to features; only for labels and analysis.
        ("is_fraud", pa.bool_()),
        ("fraud_pattern", pa.string()),
        ("attack_id", pa.string()),
        ("breached_merchant_id", pa.string()),
    ]
)

CONTRACT_COLUMNS = SCHEMA.names[:14]
GROUND_TRUTH_COLUMNS = SCHEMA.names[14:]


def write_parquet(rows: list[LabelledTxn], path: str | Path, meta: dict[str, str]) -> None:
    """Write rows in the order given. The same rows always produce byte-identical files."""
    txns = [r.txn for r in rows]
    table = pa.table(
        {
            "schema_version": [t.schema_version for t in txns],
            "txn_id": [str(t.txn_id) for t in txns],
            "card_id": [t.card_id for t in txns],
            "customer_id": [t.customer_id for t in txns],
            "amount_cents": [t.amount_cents for t in txns],
            "currency": [t.currency for t in txns],
            "merchant_id": [t.merchant_id for t in txns],
            "mcc": [t.mcc for t in txns],
            "merchant_country": [t.merchant_country for t in txns],
            "lat": [t.lat for t in txns],
            "lon": [t.lon for t in txns],
            "channel": [t.channel.value for t in txns],
            "device_id": [t.device_id for t in txns],
            "event_time": [t.event_time for t in txns],
            "is_fraud": [r.is_fraud for r in rows],
            "fraud_pattern": [r.fraud_pattern for r in rows],
            "attack_id": [r.attack_id for r in rows],
            "breached_merchant_id": [r.breached_merchant_id for r in rows],
        },
        schema=SCHEMA.with_metadata(meta),
    )
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out)
