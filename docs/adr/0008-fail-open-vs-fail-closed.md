# ADR-0008: Behaviour when the feature store is unavailable

* Status: Proposed (decide in Phase 5)

## Context
If Redis is down, the model has no history features. Approving everything lets fraud through; declining everything blocks every customer.

## Options considered
1. Fail open: approve all. Best customer experience, maximum fraud exposure.
2. Fail closed: decline all. Zero fraud, unacceptable customer impact.
3. Degraded: stateless rules plus amount-based policy (approve small, REVIEW large).

## Decision
TBD. Write down your choice, the dollar threshold, and the reasoning. Back it with the cost matrix from the model card.

## How I would explain this in an interview
TBD, in your words.
