# 05 Model card

Living document. Fill in the TBDs as Phase 2 and Phase 7 complete.

## Task

Binary classification: probability that a card authorization is fraudulent.

## Label definition

`is_fraud = 1` if a chargeback or analyst label marks it fraud. `0` if labelled legit, or if unlabelled after the label window closes (bias noted below).

## Data

Synthetic, from gateway-sim. Fraud rate target about 0.5 to 1%. Fraud patterns: stolen card travel, card testing, account takeover, merchant compromise. Document the generator version used for every trained model.

## Split

**Time-based.** Train on the earliest window, validate on the next, test on the last. Never random: a random split lets the model learn from the future and inflates every metric.

## Models compared

| Model | Purpose |
|---|---|
| Rules only | business baseline; must be beaten |
| Logistic regression | simple ML baseline |
| LightGBM | primary model |
| Isolation Forest (Phase 7) | unsupervised, catches unseen patterns |

## Metrics

* **Primary: PR-AUC.** Precision-recall curves are informative under heavy imbalance; ROC-AUC looks great even for weak models here.
* **Operating point: precision and recall at the chosen thresholds.**
* **Business: expected cost per 1,000 transactions.**
* **Calibration:** reliability curve; scores are used as probabilities in the cost math.
* Never report accuracy as a headline number.

## Thresholds from a cost matrix

| Outcome | Cost (assumption, tune and justify) |
|---|---|
| Missed fraud (approved fraud) | transaction amount |
| False decline (declined legit) | $15 customer friction + churn risk |
| Review | $3 analyst time |
| Correct approve / correct decline | $0 |

Pick `review_threshold` and `decline_threshold` to minimize expected cost on the validation set, then report on test. Show the cost curve in the README.

| Threshold | Value | Chosen on |
|---|---|---|
| review | TBD | validation |
| decline | TBD | validation |

## Explainability

LightGBM `pred_contrib=True` returns per-feature TreeSHAP contributions at prediction time with no extra dependency. Top 3 positive contributions map to reason codes in `fraudcore/reasons.py` (for example `km_from_last_txn` to `IMPOSSIBLE_TRAVEL`).

## Results

| Model | PR-AUC | Precision | Recall | Cost / 1k | Notes |
|---|---|---|---|---|---|
| Rules | TBD | TBD | TBD | TBD | |
| LogReg | TBD | TBD | TBD | TBD | |
| LightGBM | TBD | TBD | TBD | TBD | |

## Monitoring and drift

* **Population Stability Index (PSI)** on each feature and on the score distribution, live window vs training window. PSI > 0.2 raises a drift alert.
* **Performance drift** once labels mature: rolling PR-AUC and recall.

## Promotion gates (challenger to champion)

1. Offline: PR-AUC >= champion and expected cost lower on the latest holdout.
2. Shadow: at least N hours or N thousand live transactions scored.
3. Shadow: on matured labels, recall not worse by more than 1 point at equal review rate.
4. Latency: challenger p99 within budget.

## Known limitations

* Synthetic data; real fraud is messier and more adversarial.
* Unlabelled-means-legit introduces label noise.
* Analyst labels exist only for REVIEW cases (selection bias).
