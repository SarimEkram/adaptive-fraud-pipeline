# ADR-0007: Money as integer cents

* Status: Accepted

## Context
Floats cannot represent most decimal amounts exactly (0.1 + 0.2 != 0.3).

## Decision
All amounts are `int` cents in contracts, storage (BIGINT), and features. Convert to dollars only for display.

## Consequences
No rounding drift in sums; currency handling stays explicit.
