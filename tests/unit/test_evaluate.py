import numpy as np
import pytest
from ml_platform.baseline_rules import APPROVE, DECLINE, REVIEW
from ml_platform.evaluate import (
    NEVER,
    actions_from_scores,
    attack_recall,
    calibration_bins,
    choose_thresholds,
    expected_calibration_error,
    expected_cost,
    expected_cost_from_actions,
    pattern_pr_auc,
    pr_auc,
    precision_recall,
)

# Five transactions: fraud, legit, fraud, legit, legit.
Y = np.array([True, False, True, False, False])
AMOUNTS = np.array([10_000, 5_000, 20_000, 1_000, 2_000])  # cents
SCORES = np.array([0.9, 0.8, 0.2, 0.1, 0.05])


def test_scores_map_to_actions_with_inclusive_lower_edges():
    scores = np.array([0.10, 0.1499, 0.15, 0.8499, 0.85, 1.0])
    actions = actions_from_scores(scores, review_t=0.15, decline_t=0.85)
    assert list(actions) == [APPROVE, APPROVE, REVIEW, REVIEW, DECLINE, DECLINE]


def test_cost_by_hand_with_reviews_and_a_correct_decline():
    # 0.9 declined fraud: $0. 0.8 and 0.2 reviewed: 2 x $3. The rest approved legit: $0.
    # $6 over 5 transactions = $1,200 per 1,000.
    assert expected_cost(Y, SCORES, AMOUNTS, review_t=0.15, decline_t=0.85) == pytest.approx(1200)


def test_cost_of_approving_everything_is_the_fraud_dollars():
    # Missed fraud costs $100 + $200 = $300 over 5 transactions = $60,000 per 1,000.
    assert expected_cost(Y, SCORES, AMOUNTS, NEVER, NEVER) == pytest.approx(60_000)


def test_cost_of_declining_everything_is_the_false_decline_fee_on_legit_rows():
    # 3 legit rows x $15 = $45 over 5 = $9,000 per 1,000.
    assert expected_cost(Y, SCORES, AMOUNTS, 0.0, 0.0) == pytest.approx(9_000)


def test_cost_from_actions_matches_cost_from_scores():
    actions = actions_from_scores(SCORES, 0.15, 0.85)
    assert expected_cost_from_actions(Y, actions, AMOUNTS) == expected_cost(
        Y, SCORES, AMOUNTS, 0.15, 0.85
    )


def test_choose_thresholds_is_optimal_against_brute_force():
    rng = np.random.default_rng(0)
    n = 120
    y = rng.random(n) < 0.15
    scores = np.clip(rng.normal(0.25 + 0.4 * y, 0.2), 0, 1)
    amounts = rng.integers(200, 40_000, n)

    review_t, decline_t, cost = choose_thresholds(y, scores, amounts, grid=1000)

    candidates = np.append(np.unique(scores), NEVER)
    best = min(
        expected_cost(y, scores, amounts, r, d) for r in candidates for d in candidates if d >= r
    )
    assert cost == pytest.approx(best)
    assert expected_cost(y, scores, amounts, review_t, decline_t) == pytest.approx(cost)
    assert review_t <= decline_t


def test_a_perfect_model_gets_zero_cost_and_a_useless_one_does_not():
    rng = np.random.default_rng(1)
    y = rng.random(500) < 0.1
    amounts = rng.integers(500, 20_000, 500)
    perfect = y.astype(float)
    _, _, perfect_cost = choose_thresholds(y, perfect, amounts)
    noise = rng.random(500)
    _, _, noise_cost = choose_thresholds(y, noise, amounts)
    assert perfect_cost == pytest.approx(0.0)
    assert noise_cost > 1_000


def test_expensive_fraud_pushes_the_review_threshold_down():
    """When a miss costs more, it is worth reviewing more transactions."""
    rng = np.random.default_rng(2)
    y = rng.random(2000) < 0.05
    scores = np.clip(rng.normal(0.3 + 0.3 * y, 0.2), 0, 1)
    cheap, _, _ = choose_thresholds(y, scores, np.full(2000, 500))
    dear, _, _ = choose_thresholds(y, scores, np.full(2000, 50_000))
    assert dear < cheap


# --- metrics ------------------------------------------------------------------------------


def test_pr_auc_is_one_for_perfect_ranking_and_near_base_rate_for_noise():
    rng = np.random.default_rng(3)
    y = rng.random(5000) < 0.05
    assert pr_auc(y, y.astype(float)) == pytest.approx(1.0)
    assert pr_auc(y, rng.random(5000)) == pytest.approx(y.mean(), abs=0.03)


def test_precision_and_recall():
    y = np.array([True, True, True, False, False, False])
    flagged = np.array([True, True, False, True, False, False])
    precision, recall = precision_recall(y, flagged)
    assert precision == pytest.approx(2 / 3)
    assert recall == pytest.approx(2 / 3)


def test_precision_is_zero_when_nothing_is_flagged():
    assert precision_recall(np.array([True, False]), np.array([False, False])) == (0.0, 0.0)


def test_attack_recall_counts_an_attack_caught_if_any_transaction_is_flagged():
    patterns = np.array(["travel", "travel", "travel", "testing", "testing", None], dtype=object)
    attacks = np.array(["a1", "a1", "a2", "b1", "b1", None], dtype=object)
    flagged = np.array([False, True, False, True, True, False])
    result = attack_recall(patterns, attacks, flagged)
    assert result == {"travel": 0.5, "testing": 1.0}


def test_pattern_pr_auc_scores_each_pattern_against_honest_traffic():
    y = np.array([True, True, True, False, False, False, False])
    patterns = np.array(["easy", "easy", "hard", None, None, None, None], dtype=object)
    scores = np.array([0.9, 0.8, 0.3, 0.1, 0.2, 0.5, 0.05])
    result = pattern_pr_auc(y, patterns, scores)
    assert set(result) == {"easy", "hard"}
    assert result["easy"] == pytest.approx(1.0)
    assert result["hard"] < result["easy"]


def test_calibration_bins_cover_every_row_and_rise_with_the_score():
    rng = np.random.default_rng(4)
    p = rng.random(200_000) ** 4  # mostly small probabilities
    y = rng.random(200_000) < p
    bins = calibration_bins(y, p)
    assert sum(bins["size"]) == 200_000
    assert bins["predicted"] == sorted(bins["predicted"])
    assert expected_calibration_error(bins) < 0.01  # a calibrated model has a tiny error


def test_a_badly_calibrated_model_has_a_large_error():
    rng = np.random.default_rng(5)
    p = rng.random(50_000) * 0.2
    y = rng.random(50_000) < 0.5  # real rate is 50%, scores say about 10%
    assert expected_calibration_error(calibration_bins(y, p)) > 0.3
