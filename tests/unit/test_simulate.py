import hashlib
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from fraudcore.schemas import Transaction
from gateway_sim.customers import generate_population
from gateway_sim.main import main
from gateway_sim.merchants import Catalog
from gateway_sim.output import CONTRACT_COLUMNS, GROUND_TRUTH_COLUMNS, write_parquet
from gateway_sim.simulate import SHARES, LabelledTxn, simulate

START = date(2026, 1, 1)
DAYS = 30
SEED = 11
CATALOG = Catalog(SEED)


def _run(seed: int = SEED, customers: int = 300) -> list[LabelledTxn]:
    people = generate_population(customers, seed, CATALOG, START, DAYS)
    return simulate(people, CATALOG, start=START, days=DAYS, seed=seed, fraud_rate=0.01)


@pytest.fixture(scope="module")
def rows() -> list[LabelledTxn]:
    return _run()


def test_fraud_rate_is_about_one_percent(rows: list[LabelledTxn]) -> None:
    rate = sum(r.is_fraud for r in rows) / len(rows)
    assert 0.008 < rate < 0.013


def test_rows_are_in_event_time_order_with_unique_ids(rows: list[LabelledTxn]) -> None:
    times = [r.txn.event_time for r in rows]
    assert times == sorted(times)
    assert len({r.txn.txn_id for r in rows}) == len(rows)


def test_every_pattern_appears_and_case_shares_are_close(rows: list[LabelledTxn]) -> None:
    cases = defaultdict(set)
    for r in rows:
        if r.is_fraud:
            cases[r.fraud_pattern].add(r.attack_id)
    assert set(cases) == set(SHARES)
    total = sum(len(v) for v in cases.values())
    for name, share in SHARES.items():
        spread = 3 * (share * (1 - share) / total) ** 0.5  # three standard deviations of noise
        assert abs(len(cases[name]) / total - share) < spread


def test_ground_truth_is_consistent(rows: list[LabelledTxn]) -> None:
    by_attack: dict[str, list[LabelledTxn]] = defaultdict(list)
    for r in rows:
        if r.is_fraud:
            assert r.fraud_pattern and r.attack_id
            by_attack[r.attack_id].append(r)
        else:
            assert r.fraud_pattern is None and r.attack_id is None
            assert r.breached_merchant_id is None
    for attack in by_attack.values():
        assert len({r.txn.card_id for r in attack}) == 1  # one attack hits one card
        assert len({r.fraud_pattern for r in attack}) == 1


def test_fraud_stays_inside_the_simulated_window(rows: list[LabelledTxn]) -> None:
    honest_last = max(r.txn.event_time for r in rows if not r.is_fraud)
    assert max(r.txn.event_time for r in rows) <= honest_last


def test_travel_fraud_follows_a_genuine_purchase_by_the_same_card(rows: list[LabelledTxn]) -> None:
    honest_by_card = defaultdict(list)
    for r in rows:
        if not r.is_fraud:
            honest_by_card[r.txn.card_id].append(r.txn.event_time)
    first_fraud = {}
    for r in rows:
        if r.fraud_pattern == "stolen_card_travel" and r.attack_id not in first_fraud:
            first_fraud[r.attack_id] = r.txn
    assert first_fraud
    for t in first_fraud.values():
        before = [
            h for h in honest_by_card[t.card_id]
            if timedelta(minutes=20) <= t.event_time - h <= timedelta(hours=6)
        ]  # fmt: skip
        assert before  # the card was genuinely used at home just before


def test_breach_victims_all_shopped_at_the_breached_merchant_first(
    rows: list[LabelledTxn],
) -> None:
    first_visit: dict[tuple[str, str], object] = {}
    for r in rows:
        if not r.is_fraud:
            first_visit.setdefault((r.txn.card_id, r.txn.merchant_id), r.txn.event_time)
    breaches = defaultdict(set)
    for r in rows:
        if r.fraud_pattern == "merchant_compromise":
            assert r.breached_merchant_id
            breaches[r.breached_merchant_id].add(r.txn.card_id)
            visit = first_visit[(r.txn.card_id, r.breached_merchant_id)]
            assert visit < r.txn.event_time  # type: ignore[operator]
    assert breaches
    assert all(len(cards) >= 2 for cards in breaches.values())  # many cards share one shop


def test_same_seed_same_rows_different_seed_different_rows(rows: list[LabelledTxn]) -> None:
    assert _run() == rows
    assert _run(seed=12) != rows


def test_zero_days_gives_no_rows() -> None:
    people = generate_population(20, 1, CATALOG, START, 1)
    assert simulate(people, CATALOG, start=START, days=0, seed=1, fraud_rate=0.01) == []


# --- parquet ------------------------------------------------------------------------------


def test_parquet_has_contract_then_ground_truth_columns(
    rows: list[LabelledTxn], tmp_path: Path
) -> None:
    path = tmp_path / "t.parquet"
    write_parquet(rows, path, {"generator_version": "test"})
    table = pq.read_table(path)
    assert table.column_names == CONTRACT_COLUMNS + GROUND_TRUTH_COLUMNS
    assert table.num_rows == len(rows)
    assert str(table.schema.field("amount_cents").type) == "int64"  # ADR-0007
    assert table.schema.metadata[b"generator_version"] == b"test"


def test_parquet_rows_satisfy_the_transaction_contract(
    rows: list[LabelledTxn], tmp_path: Path
) -> None:
    path = tmp_path / "t.parquet"
    write_parquet(rows, path, {})
    for record in pq.read_table(path, columns=CONTRACT_COLUMNS).to_pylist()[:500]:
        Transaction.model_validate(record)


def test_parquet_files_are_byte_identical_for_the_same_rows(
    rows: list[LabelledTxn], tmp_path: Path
) -> None:
    a, b = tmp_path / "a.parquet", tmp_path / "b.parquet"
    write_parquet(rows, a, {"seed": "1"})
    write_parquet(_run(), b, {"seed": "1"})
    assert hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()


# --- command line -------------------------------------------------------------------------


def test_cli_writes_a_file_and_is_reproducible(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    args = ["--offline", "--customers", "120", "--days", "20", "--seed", "5"]
    main([*args, "--out", str(tmp_path / "one.parquet")])
    main([*args, "--out", str(tmp_path / "two.parquet")])
    assert (tmp_path / "one.parquet").read_bytes() == (tmp_path / "two.parquet").read_bytes()
    out = capsys.readouterr().out
    assert "fraud:" in out and "generator" in out
    meta = pq.read_schema(tmp_path / "one.parquet").metadata
    assert meta[b"seed"] == b"5" and meta[b"days"] == b"20"


def test_cli_refuses_live_mode_for_now() -> None:
    with pytest.raises(SystemExit):
        main(["--days", "5"])
