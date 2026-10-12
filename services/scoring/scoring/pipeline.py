"""The hot path. Every step here costs latency; see the budget in docs/02 section 5."""

from __future__ import annotations

from fraudcore.config import Settings
from fraudcore.schemas import Decision, Transaction
from scoring.model import ModelRegistry


class ScoringPipeline:
    def __init__(self, settings: Settings, registry: ModelRegistry) -> None:
        self.settings = settings
        self.registry = registry
        # TODO(phase 4): inject CardStateStore, idempotency store, publisher

    async def score(self, txn: Transaction) -> Decision:
        """TODO(phase 3, then phase 4). Steps, in order:

        1. Idempotency: if txn_id already decided, return the stored decision (F5).
        2. Load card state (Redis). On timeout, switch to fallback mode (F1, ADR-0008).
        3. features = compute_features(txn, state)          # BEFORE update
        4. rules_fired = evaluate_rules(features, txn)
        5. champion score + contributions; challenger shadow score (skip under load, F9)
        6. action = decide(score, rules_fired, thresholds)
        7. reasons = top 3 positive contributions mapped to reason codes
        8. save update_state(txn, state) and the decision under the idempotency key
        9. publish ScoredEvent without awaiting delivery (ADR-0002)
        """
        raise NotImplementedError
