"""Replay, training and evaluation end to end on a small simulated world."""

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import numpy as np
import pyarrow.parquet as pq
import pytest
from fraudcore.features import FEATURE_NAMES, CardState, compute_features, update_state
from fraudcore.schemas import Channel, Transaction
from gateway_sim.customers import generate_population
from gateway_sim.merchants import Catalog
from gateway_sim.output import write_parquet
from gateway_sim.simulate import simulate
from ml_platform import evaluate, train
from ml_platform.registry import latest_version_dir, read_metadata
from ml_platform.replay import (
    IDENTIFIER_COLUMNS,
    LABEL_COLUMNS,
    build_feature_table,
    replay_features,
)
from ml_platform.split import time_split

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def txn(card: str, at: datetime, amount: int = 1000, merchant: str = "m1") -> Transaction:
    return Transaction(
        txn_id=uuid4(),
        card_id=card,
        customer_id="u",
        amount_cents=amount,
        currency="CAD",
        merchant_id=merchant,
        mcc="5411",
        merchant_country="CA",
        lat=43.65,
        lon=-79.38,
        channel=Channel.CARD_PRESENT,
        event_time=at,
    )


# --- replay on hand-built sequences -------------------------------------------------------


def test_replay_gives_the_hand_computed_features():
    seq = [txn("a", T0 + timedelta(seconds=s)) for s in (0, 10, 20)]
    first, second, third = list(replay_features(seq))
    assert first["txn_count_1m"] == 0 and first["secs_since_last_txn"] == -1  # cold start
    assert second["txn_count_1m"] == 1 and second["secs_since_last_txn"] == 10
    assert third["txn_count_1m"] == 2 and third["secs_since_last_txn"] == 10


def test_cards_do_not_share_state():
    seq = [txn("a", T0), txn("b", T0 + timedelta(seconds=1)), txn("a", T0 + timedelta(seconds=2))]
    a1, b1, a2 = list(replay_features(seq))
    assert b1["txn_count_1m"] == 0  # card b has no history, though a has
    assert a2["txn_count_1m"] == 1  # card a sees only its own earlier transaction


def test_replay_never_looks_ahead():
    """Features for the first k transactions are the same whether or not later ones exist."""
    seq = [txn("a" if i % 3 else "b", T0 + timedelta(seconds=7 * i), 500 + i) for i in range(60)]
    prefix = list(replay_features(seq[:25]))
    full = list(replay_features(seq))[:25]
    assert prefix == full


# --- a small simulated world --------------------------------------------------------------


@pytest.fixture(scope="module")
def world(tmp_path_factory) -> dict[str, Path]:
    tmp = tmp_path_factory.mktemp("world")
    start, days, seed = date(2026, 1, 1), 40, 3
    catalog = Catalog(seed)
    people = generate_population(150, seed, catalog, start, days)
    rows = simulate(people, catalog, start=start, days=days, seed=seed, fraud_rate=0.02)
    write_parquet(rows, tmp / "txns.parquet", {"generator_version": "test", "seed": str(seed)})
    build_feature_table(tmp / "txns.parquet", tmp / "features.parquet")
    return {"tmp": tmp, "txns": tmp / "txns.parquet", "features": tmp / "features.parquet"}


def test_feature_table_has_identifiers_labels_and_every_feature(world):
    table = pq.read_table(world["features"])
    assert table.column_names == IDENTIFIER_COLUMNS + LABEL_COLUMNS + FEATURE_NAMES
    assert table.num_rows == pq.read_table(world["txns"]).num_rows
    times = table.column("event_time").to_pylist()
    assert times == sorted(times)


def test_every_cards_first_row_is_a_cold_start(world):
    df, _ = train.load_features(world["features"])
    first = df.groupby("card_id").head(1)
    assert (first["txn_count_24h"] == 0).all()
    assert (first["km_from_last_txn"] == -1).all()
    assert (first["secs_since_last_txn"] == -1).all()


def test_table_matches_an_independent_replay_of_one_busy_card(world):
    source = pq.read_table(world["txns"]).select(list(Transaction.model_fields)).to_pylist()
    df, _ = train.load_features(world["features"])
    busiest = df["card_id"].value_counts().index[0]
    mine = sorted(
        (Transaction.model_validate(r) for r in source if r["card_id"] == busiest),
        key=lambda t: (t.event_time, str(t.txn_id)),
    )
    state, expected = CardState(busiest), []
    for t in mine:
        expected.append(compute_features(t, state))
        state = update_state(t, state)
    got = df[df["card_id"] == busiest][FEATURE_NAMES].to_dict("records")
    assert got == expected


def test_only_the_sixteen_features_ever_reach_a_model(world):
    df, _ = train.load_features(world["features"])
    X = train.feature_matrix(df)
    assert list(X.columns) == FEATURE_NAMES
    assert not {"is_fraud", "fraud_pattern", "attack_id", "txn_id", "card_id"} & set(X.columns)


# --- training and evaluation --------------------------------------------------------------


def test_models_train_and_lightgbm_knows_its_feature_names(world):
    df, _ = train.load_features(world["features"])
    models = train.fit_models(df, time_split(train.event_times(df)))
    assert set(models) == {"amount_only", "logreg", "lightgbm"}
    assert models["lightgbm"].best_iteration_ >= 1
    assert models["lightgbm"].booster_.feature_name() == FEATURE_NAMES
    scores = models["lightgbm"].predict_proba(train.feature_matrix(df))[:, 1]
    assert scores.min() >= 0 and scores.max() <= 1


def test_train_then_evaluate_from_the_command_line_functions(world):
    models_dir, plot = world["tmp"] / "models", world["tmp"] / "plot.png"
    train.run(["--features", str(world["features"]), "--models", str(models_dir)])
    evaluate.run(
        ["--features", str(world["features"]), "--models", str(models_dir), "--plot", str(plot)]
    )

    version_dir = latest_version_dir(models_dir)
    for name in (
        "model.txt",
        "logreg.joblib",
        "amount_only.joblib",
        "metadata.json",
        "results.json",
    ):
        assert (version_dir / name).exists()
    assert plot.exists()

    meta = read_metadata(version_dir)
    assert meta["version"] == "v0001" and meta["generator_version"] == "test"
    assert meta["feature_names"] == FEATURE_NAMES
    assert set(meta["thresholds"]) == {"amount_only", "logreg", "lightgbm"}
    for pair in meta["thresholds"].values():
        assert pair["review"] <= pair["decline"]

    results = json.loads((version_dir / "results.json").read_text())
    df, _ = train.load_features(world["features"])
    test_rows = time_split(train.event_times(df))["test"]
    base_rate = float(df["is_fraud"][test_rows].mean())
    for name in evaluate.MODELS:
        assert 0 <= results[name]["test_pr_auc"] <= 1
    assert results["lightgbm"]["test_pr_auc"] > 3 * base_rate  # far better than guessing
    assert results["lightgbm"]["test_cost"] < results["approve_all"]["test_cost"]


def test_windows_in_metadata_are_in_time_order(world):
    version_dir = latest_version_dir(world["tmp"] / "models")
    windows = read_metadata(version_dir)["windows"]
    assert windows["train"]["end"] < windows["val"]["start"]
    assert windows["val"]["end"] < windows["test"]["start"]
    assert np.sum([w["rows"] for w in windows.values()]) > 0


def test_ablation_scores_every_feature_removal(world):
    from ml_platform.ablate import ablation

    df, _ = train.load_features(world["features"])
    scores = ablation(df, time_split(train.event_times(df)))
    assert set(scores) == {"all features"} | {f"without {f}" for f in FEATURE_NAMES}
    assert all(0 <= v <= 1 for v in scores.values())
