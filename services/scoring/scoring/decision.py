"""Turn a score and fired rules into an action and reason codes."""

from __future__ import annotations

from fraudcore.schemas import Action, Reason

from scoring.rules import Rule


def decide(score: float, rules_fired: list[Rule], review_t: float, decline_t: float) -> Action:
    """TODO(phase 3): thresholds give a base action; a fired rule can only make it stricter.

    Severity order: APPROVE < REVIEW < DECLINE. Thresholds come from the cost matrix (docs/05).
    """
    raise NotImplementedError


def top_reasons(feature_names: list[str], contributions: list[float], k: int = 3) -> list[Reason]:
    """TODO(phase 3): top k POSITIVE contributions (pushing toward fraud) as Reason objects.

    LightGBM pred_contrib returns one value per feature plus a final bias term; drop the bias.
    """
    raise NotImplementedError
