"""Hard rules. They run alongside the model and can force an action.

Rules are good at things that are always suspicious; the model is good at combinations.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fraudcore.schemas import Action, Transaction

Features = dict[str, float]


@dataclass(frozen=True)
class Rule:
    name: str
    min_action: Action  # the rule forces at least this action
    check: Callable[[Features, Transaction], bool]


# Worked example. Write the rest yourself.
IMPOSSIBLE_TRAVEL = Rule(
    name="IMPOSSIBLE_TRAVEL",
    min_action=Action.DECLINE,
    check=lambda f, _t: f["implied_speed_kmh"] > 1000,  # faster than a plane
)

RULES: list[Rule] = [
    IMPOSSIBLE_TRAVEL,
    # TODO(phase 3): CARD_TESTING (many small txns in 10 min), HIGH_RISK_NEW_DEVICE, ...
]


def evaluate_rules(features: Features, txn: Transaction) -> list[Rule]:
    return [r for r in RULES if r.check(features, txn)]
