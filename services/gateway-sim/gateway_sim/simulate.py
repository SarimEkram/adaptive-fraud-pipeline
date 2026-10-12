"""Runs the simulated world: honest traffic first, then fraud attacks mixed in.

Ground truth (which rows are fraud, and which attack) is kept next to each transaction but
is never part of the `Transaction` contract, so it cannot leak into features.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import numpy as np
from fraudcore.schemas import Channel, Transaction

from gateway_sim.customers import Customer, daily_transactions, location_at, random_time_on
from gateway_sim.merchants import Catalog
from gateway_sim.patterns import PATTERNS

GENERATOR_VERSION = "1.0.0"  # bump whenever the generated data would change (model card)

# Share of fraud *cases* (attacks) by pattern, from the Phase 1 design note.
SHARES = {
    "stolen_card_travel": 0.30,
    "card_testing": 0.35,
    "account_takeover": 0.25,
    "merchant_compromise": 0.10,
}
CAMPAIGN_VICTIMS = (10, 30)  # cards hit in one merchant breach
_MIN_CAMPAIGN_SHOPPERS = 8  # a breached shop needs enough customers to hurt several cards
_ATTACK_ROOM = timedelta(hours=8)  # an attack must finish before the simulation ends
_CAMPAIGN_ROOM = timedelta(days=4)
_CAMPAIGN_LEAD = timedelta(days=3)  # history that must exist before a breach
_MAX_MISSES = 1_000
_HABIT_TIMING = 0.6  # share of attacks timed like the victim's own shopping
_MAX_CAMPAIGN_TRIES = 200
_COMPROMISE_TXNS_PER_CASE = 1.3  # 70% of cases are one purchase, 30% are two


@dataclass(frozen=True)
class LabelledTxn:
    txn: Transaction
    is_fraud: bool = False
    fraud_pattern: str | None = None
    attack_id: str | None = None  # one id per victim card per attack
    breached_merchant_id: str | None = None  # set only for merchant-compromise rows


def _first_visits(honest: list[Transaction]) -> dict[str, dict[str, datetime]]:
    """merchant_id -> {customer_id: first time that customer shopped there}."""
    visits: dict[str, dict[str, datetime]] = {}
    for t in honest:
        first = visits.setdefault(t.merchant_id, {})
        if t.customer_id not in first or t.event_time < first[t.customer_id]:
            first[t.customer_id] = t.event_time
    return visits


def _campaign(
    by_id: dict[str, Customer],
    visits: dict[str, dict[str, datetime]],
    begin: datetime,
    end: datetime,
    rng: np.random.Generator,
) -> list[tuple[Customer, datetime, str | None]]:
    """One breached shop and the cards that had already shopped there before the breach."""
    low, high = begin + _CAMPAIGN_LEAD, end - _CAMPAIGN_ROOM
    shops = sorted(m for m, v in visits.items() if len(v) >= _MIN_CAMPAIGN_SHOPPERS)
    if high <= low or not shops:
        return []
    merchant = shops[int(rng.integers(len(shops)))]
    breach = low + timedelta(seconds=int(rng.integers(int((high - low).total_seconds()))))
    eligible = sorted(c for c, first in visits[merchant].items() if first < breach)
    if len(eligible) < 5:
        return []
    wanted = int(rng.integers(CAMPAIGN_VICTIMS[0], CAMPAIGN_VICTIMS[1] + 1))
    picks = rng.choice(len(eligible), size=min(wanted, len(eligible)), replace=False)
    return [
        (by_id[eligible[int(i)]], breach + timedelta(minutes=int(rng.integers(0, 4321))), merchant)
        for i in picks
    ]


def simulate(
    customers: list[Customer],
    catalog: Catalog,
    *,
    start: date,
    days: int,
    seed: int,
    fraud_rate: float,
) -> list[LabelledTxn]:
    """Every transaction for `days` days, honest and fraudulent, in event-time order."""
    by_id = {c.customer_id: c for c in customers}
    honest_rng = np.random.default_rng([seed, 2])
    honest = [
        t
        for d in range(days)
        for c in customers
        for t in daily_transactions(c, start + timedelta(days=d), honest_rng, catalog)
    ]
    if not honest:
        return []
    begin = min(t.event_time for t in honest)
    end = max(t.event_time for t in honest)
    span = (end - _ATTACK_ROOM - begin).total_seconds()
    if span <= 0:
        raise ValueError("simulation is too short to fit an attack; use more days")

    # Travel fraud needs a genuine in-person purchase at home just before it.
    anchors = [
        t
        for t in honest
        if t.channel == Channel.CARD_PRESENT
        and t.event_time <= end - _ATTACK_ROOM
        and location_at(by_id[t.customer_id], t.event_time) == by_id[t.customer_id].home_area
    ]
    visits = _first_visits(honest)

    # Stage 1: single-victim attacks, picked by their share of cases. Stop a little early to
    # leave room for the merchant-compromise campaigns of stage 2, so the total lands on target.
    share = SHARES["merchant_compromise"]
    compromise_per_other_case = share / (1 - share)
    others = [k for k in SHARES if k != "merchant_compromise"]
    weights = np.array([SHARES[k] for k in others])
    weights /= weights.sum()

    target = round(len(honest) * fraud_rate / (1 - fraud_rate))
    rng = np.random.default_rng([seed, 3])
    fraud: list[LabelledTxn] = []
    attacks = 0

    def place(kind: str, cases: list[tuple[Customer, datetime, str | None]]) -> int:
        """Generate the attacks for these cases; return how many produced transactions."""
        nonlocal attacks
        placed = 0
        for victim, now, breached in cases:
            txns = PATTERNS[kind].generate(victim, now, rng, catalog)
            if txns:
                attacks += 1
                placed += 1
                attack_id = f"{kind}-{attacks:05d}"
                fraud.extend(LabelledTxn(t, True, kind, attack_id, breached) for t in txns)
        return placed

    other_cases = misses = 0
    while len(fraud) + _COMPROMISE_TXNS_PER_CASE * compromise_per_other_case * other_cases < target:
        kind = others[int(rng.choice(len(others), p=weights))]
        if kind == "stolen_card_travel":
            anchor = anchors[int(rng.integers(len(anchors)))] if anchors else None
            cases = [(by_id[anchor.customer_id], anchor.event_time, None)] if anchor else []
        else:
            who = customers[int(rng.integers(len(customers)))]
            when = begin + timedelta(seconds=int(rng.integers(int(span))))
            if rng.random() < _HABIT_TIMING:  # many intruders act at ordinary hours
                when = min(random_time_on(who, when.date(), rng), end - _ATTACK_ROOM)
            cases = [(who, when, None)]
        placed = place(kind, cases)
        other_cases += placed
        misses = 0 if placed else misses + 1
        if misses > _MAX_MISSES:
            raise ValueError("could not place any attacks; use more customers or days")

    # Stage 2: breaches, until compromise cases are their share of all cases. If the world is
    # too small to have a breach (few shoppers per shop, short run), there are simply none.
    wanted = round(other_cases * compromise_per_other_case)
    done = tries = 0
    while done < wanted and tries < _MAX_CAMPAIGN_TRIES:
        tries += 1
        cases = _campaign(by_id, visits, begin, end, rng)[: wanted - done]
        done += place("merchant_compromise", cases)

    rows = [LabelledTxn(t) for t in honest] + fraud
    rows.sort(key=lambda r: (r.txn.event_time, str(r.txn.txn_id)))
    return rows
