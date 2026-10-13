# ml-platform

Batch jobs. Nothing here is on the hot path.

Typical Phase 2 run (needs `brew install libomp` on macOS for LightGBM):

```bash
python -m gateway_sim.main --offline --customers 4000 --days 60   # data/txns.parquet
mlp replay      # data/features.parquet, via fraudcore.features (no second implementation)
mlp train       # models/versions/v0001: LightGBM, logistic regression, amount-only baseline
mlp evaluate    # results table, thresholds from the cost matrix, docs/images/phase2-results.png
mlp ablate      # drop-one-feature test PR-AUC
```

Files: `replay.py`, `split.py` (time-based), `baseline_rules.py`, `train.py`, `evaluate.py` (cost matrix, threshold search), `report.py`, `ablate.py`, `registry.py`.

```
mlp replay    # events -> feature table, via fraudcore (ADR-0006)
mlp train     # LightGBM + baselines on time-based split
mlp evaluate  # PR-AUC, cost curve, thresholds -> model card
mlp drift     # PSI live vs training window
mlp promote   # gates from docs/05, atomic champion swap
```

Original designation: you write replay, evaluate, drift, promote; Claude can help with CLI, plots, registry plumbing. Current working mode (see `CLAUDE.md`): Claude writes the code, explains it line by line, and the author restates the key idea.
