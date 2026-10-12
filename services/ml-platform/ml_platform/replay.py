"""Build the training table by replaying events through fraudcore (ADR-0006).

for each transaction in event_time order:
    state = states.get(card_id) or CardState(card_id)
    row = compute_features(txn, state)     # point-in-time correct by construction
    states[card_id] = update_state(txn, state)
"""


def run(argv: list[str]) -> None:
    raise NotImplementedError  # TODO(phase 2)
