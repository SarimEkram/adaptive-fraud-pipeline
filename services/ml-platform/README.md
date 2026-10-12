# ml-platform

Batch jobs. Nothing here is on the hot path.

```
mlp replay    # events -> feature table, via fraudcore (ADR-0006)
mlp train     # LightGBM + baselines on time-based split
mlp evaluate  # PR-AUC, cost curve, thresholds -> model card
mlp drift     # PSI live vs training window
mlp promote   # gates from docs/05, atomic champion swap
```

Original designation: you write replay, evaluate, drift, promote; Claude can help with CLI, plots, registry plumbing. Current working mode (see `CLAUDE.md`): Claude writes the code, explains it line by line, and the author restates the key idea.
