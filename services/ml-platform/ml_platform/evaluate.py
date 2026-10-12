"""Metrics and threshold selection.

* PR-AUC, precision and recall at thresholds, calibration curve
* expected cost per 1k txns using the cost matrix in docs/05
* choose review and decline thresholds on VALIDATION, report on TEST
"""


def expected_cost(y_true, scores, amounts_cents, review_t: float, decline_t: float) -> float:
    raise NotImplementedError  # TODO(phase 2)


def run(argv: list[str]) -> None:
    raise NotImplementedError  # TODO(phase 2)
