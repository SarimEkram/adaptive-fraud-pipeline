# 04 Feature catalog

Every feature lives in `libs/fraudcore/fraudcore/features/compute.py`, is computed from `(transaction, card_state_before_transaction)`, and appears in this table. If it is not in this table, it does not ship.

| Feature | Definition | Why it catches fraud | State needed |
|---|---|---|---|
| txn_count_1m | card txns in last 60 s | bursts, card testing | recent events |
| txn_count_1h | card txns in last hour | velocity | recent events |
| txn_count_24h | card txns in last day | velocity baseline | recent events |
| amount_sum_1h_cents | total spend last hour | cash-out sprees | recent events |
| small_txn_count_10m | txns under $2 in last 10 min | card testing probes | recent events |
| amount_zscore | (amount - card mean) / card std | unusual size for this customer | running mean, M2 (Welford) |
| secs_since_last_txn | seconds since previous txn | bursts | last txn |
| km_from_last_txn | haversine distance to previous txn | stolen card used elsewhere | last location |
| implied_speed_kmh | km / hours since last txn | impossible travel | last location + time |
| is_foreign | merchant_country != home_country | cross-border misuse | home country |
| is_new_device | device not seen for this card | account takeover | known devices |
| is_new_merchant | merchant not seen for this card | unfamiliar spend | known merchants |
| mcc_risk_bucket | category risk tier (gift cards, crypto, wire = high) | cash-like goods | none (static map) |
| hour_of_day | local hour of event | 3 am spend | none |
| is_ecommerce | channel == ecommerce | card-not-present risk | none |
| amount_cents | raw amount | | none |

## Exact definitions (as implemented in `compute.py`)

All values are floats, in the column order of `FEATURE_NAMES`. "Window W" means events in `[event_time - W, event_time)`: an event exactly W earlier counts, one at the same instant or later does not.

| Feature | Exact definition | Cold start (empty state) |
|---|---|---|
| amount_cents | the transaction's amount in integer cents, as a float | the amount |
| txn_count_1m / 1h / 24h | number of prior events in window 1 min / 1 h / 24 h | 0 |
| amount_sum_1h_cents | sum of those amounts over window 1 h | 0 |
| small_txn_count_10m | prior events in window 10 min with amount strictly under 200 cents | 0 |
| amount_zscore | `(amount - mean) / max(std, 100)` with Welford running mean and sample std over the card's lifetime; 0 if fewer than 3 prior amounts | 0 |
| secs_since_last_txn | seconds since the latest earlier event, never below 0 | -1 |
| km_from_last_txn | haversine distance to that event's location | -1 |
| implied_speed_kmh | km / hours, with elapsed time floored at 60 s | -1 |
| is_foreign | 1 if merchant country differs from the card's home country (the first transaction's country) | 0 |
| is_new_device | 1 if the device id was never seen on the card; 0 for card-present (no device) | 0 or 1 |
| is_new_merchant | 1 if the merchant id was never seen on the card | 1 |
| mcc_risk_bucket | 2 high (5815, 5816, 6051, 4829, 7995), 1 elevated (5732, 5944, 5947), else 0 | static |
| hour_of_day | `(UTC hour + round(lon / 15)) mod 24`, local mean solar time | static |
| is_ecommerce | 1 if channel is ecommerce | static |

Notes:

* The strict "before" edge protects the count features even if the ordering rule were broken, but `is_new_*`, distance, elapsed time and z-score would still leak, so the rule stays.
* Late events: scored normally, never move `last_*` backwards, elapsed time clamped at 0. Windows older than 24 h behind the newest event are pruned, so a very late event sees a shorter history (accepted limitation).
* State is bounded: events older than 24 h behind the newest are dropped, known devices and merchants are capped at 50 with least-recently-used eviction.

## Rules for features

1. **Point-in-time.** Only events strictly before `txn.event_time`. Unit test this for every windowed feature.
2. **Bounded state.** Windows are pruned on update; known-device and known-merchant sets are capped (LRU) so one card cannot grow state forever.
3. **Cold start.** A brand-new card has empty state. Every feature must return a defined value (and the model must see cold-start examples in training).
4. **No leakage.** Never use the label, the decision, or anything known only after the decision.

## Adding a feature checklist

- [ ] Row added above with a fraud rationale
- [ ] Implemented in `compute.py`, state handled in `update_state`
- [ ] Unit test including the point-in-time boundary
- [ ] Parity test still passes
- [ ] Ablation: model with vs without it, result noted in the model card
