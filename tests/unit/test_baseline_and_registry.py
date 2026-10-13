import numpy as np
import pandas as pd
import pytest
from fraudcore.features import FEATURE_NAMES
from ml_platform.baseline_rules import APPROVE, DECLINE, REVIEW, rules_actions
from ml_platform.registry import latest_version_dir, new_version_dir, read_metadata, write_metadata


def rows(**overrides) -> pd.DataFrame:
    """One ordinary row, with some features overridden."""
    base = {name: 0.0 for name in FEATURE_NAMES}
    base.update(amount_cents=1500.0, secs_since_last_txn=3600.0, implied_speed_kmh=5.0)
    base.update(overrides)
    return pd.DataFrame([base])


def action(**overrides) -> int:
    return int(rules_actions(rows(**overrides))[0])


def test_an_ordinary_transaction_is_approved():
    assert action() == APPROVE


def test_impossible_travel_is_declined():
    assert action(implied_speed_kmh=1500.0, km_from_last_txn=2000.0) == DECLINE


def test_fast_but_short_distance_is_not_impossible_travel():
    assert action(implied_speed_kmh=900.0, km_from_last_txn=50.0) == APPROVE


def test_a_run_of_tiny_charges_is_declined_as_card_testing():
    assert action(small_txn_count_10m=4.0) == DECLINE
    assert action(small_txn_count_10m=3.0) == APPROVE


def test_new_device_with_a_large_amount_is_reviewed():
    assert action(is_new_device=1.0, amount_cents=12_000.0) == REVIEW
    assert action(is_new_device=1.0, amount_cents=2_000.0) == APPROVE


def test_high_risk_category_with_a_large_amount_is_reviewed():
    assert action(mcc_risk_bucket=2.0, amount_cents=6_000.0) == REVIEW
    assert action(mcc_risk_bucket=1.0, amount_cents=6_000.0) == APPROVE


def test_decline_beats_review_when_both_rules_fire():
    assert action(is_new_device=1.0, amount_cents=20_000.0, small_txn_count_10m=5.0) == DECLINE


def test_rules_work_on_many_rows_at_once():
    frame = pd.concat([rows(), rows(small_txn_count_10m=9.0), rows(txn_count_1m=6.0)])
    assert list(rules_actions(frame)) == [APPROVE, DECLINE, REVIEW]


# --- registry -----------------------------------------------------------------------------


def test_versions_count_up_and_latest_is_the_newest(tmp_path):
    first, first_dir = new_version_dir(tmp_path)
    second, second_dir = new_version_dir(tmp_path)
    assert (first, second) == ("v0001", "v0002")
    assert latest_version_dir(tmp_path) == second_dir
    assert first_dir.exists() and second_dir.exists()


def test_latest_without_any_version_explains_what_to_do(tmp_path):
    with pytest.raises(FileNotFoundError, match="mlp train"):
        latest_version_dir(tmp_path / "none")


def test_metadata_round_trips(tmp_path):
    _, path = new_version_dir(tmp_path)
    write_metadata(
        path, {"version": "v0001", "thresholds": {"review": 0.1}, "n": np.int64(3).item()}
    )
    assert read_metadata(path)["thresholds"] == {"review": 0.1}
