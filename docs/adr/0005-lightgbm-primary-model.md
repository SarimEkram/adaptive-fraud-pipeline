# ADR-0005: LightGBM as the primary model

* Status: Proposed (confirm with Phase 2 results)

## Context
Tabular, heavily imbalanced data; sub-5 ms inference; explanations required.

## Options considered
1. Logistic regression: fast and interpretable, misses feature interactions.
2. Gradient-boosted trees (LightGBM / XGBoost): state of the art on tabular data, fast, native TreeSHAP.
3. Neural networks: no advantage on this data, slower, harder to explain.

## Decision
LightGBM, pending evidence that it beats rules and logistic regression on PR-AUC and cost.

## Consequences
Explanations via `pred_contrib=True` with no extra dependency. Must handle imbalance with `scale_pos_weight` or class weights, and check calibration.
