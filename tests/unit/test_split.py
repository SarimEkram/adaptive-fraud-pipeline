import numpy as np
import pytest
from ml_platform.split import DAY, time_split

START = np.datetime64("2026-01-01T00:00:00")


def _hourly(days: int) -> np.ndarray:
    return START + np.arange(days * 24) * np.timedelta64(1, "h")


def test_windows_are_disjoint_and_in_time_order():
    times = _hourly(60)
    masks = time_split(times)
    assert not (masks["train"] & masks["val"]).any()
    assert not (masks["val"] & masks["test"]).any()
    assert not (masks["train"] & masks["test"]).any()
    # Every training row is earlier than every validation row, which is earlier than every test row.
    assert times[masks["train"]].max() < times[masks["val"]].min()
    assert times[masks["val"]].max() < times[masks["test"]].min()


def test_a_gap_of_at_least_one_day_separates_the_windows():
    times = _hourly(60)
    masks = time_split(times)
    assert times[masks["val"]].min() - times[masks["train"]].max() >= DAY
    assert times[masks["test"]].min() - times[masks["val"]].max() >= DAY


def test_gap_rows_belong_to_no_set():
    masks = time_split(_hourly(60))
    used = masks["train"] | masks["val"] | masks["test"]
    assert 0 < (~used).sum() < 0.1 * len(used)


def test_default_proportions_are_roughly_sixty_twenty_twenty_of_the_time_span():
    times = _hourly(100)
    masks = time_split(times)
    assert masks["train"].mean() == pytest.approx(0.60, abs=0.02)
    assert masks["val"].mean() == pytest.approx(0.20, abs=0.02)
    assert masks["test"].mean() == pytest.approx(0.18, abs=0.03)


def test_the_split_does_not_depend_on_row_order():
    times = _hourly(60)
    shuffled = np.random.default_rng(0).permutation(times)
    a, b = time_split(times), time_split(shuffled)
    for name in a:
        assert (np.sort(times[a[name]]) == np.sort(shuffled[b[name]])).all()


@pytest.mark.parametrize("train,val", [(0.0, 0.2), (0.6, 0.0), (0.8, 0.3)])
def test_bad_shares_are_rejected(train, val):
    with pytest.raises(ValueError):
        time_split(_hourly(60), train_share=train, val_share=val)


def test_too_little_time_for_the_gaps_is_rejected():
    with pytest.raises(ValueError):
        time_split(_hourly(3))
