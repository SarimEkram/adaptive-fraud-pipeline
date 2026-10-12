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
