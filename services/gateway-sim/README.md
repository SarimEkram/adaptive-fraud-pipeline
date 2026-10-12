# gateway-sim

Plays three roles: merchants (normal spend), fraudsters (attack patterns), and the issuer (chargebacks arriving late).

| File | Role | Owner |
|---|---|---|
| customers.py | realistic customer population | **you write** |
| patterns.py | fraud attack patterns | **you write** |
| main.py | rate-controlled loop, sends to scoring, schedules chargebacks | Claude can help |
| control.py | small API the dashboard calls to launch attacks | Claude can help |

The Owner column is the original designation. Current working mode (see `CLAUDE.md`): Claude writes the code, explains it line by line, and the author restates the key idea.

Phase 1 runs offline; Phase 4 runs live.

```bash
python -m gateway_sim.main --offline --customers 1000 --days 30 --seed 42 --out data/txns.parquet
python notebooks/phase1_plots.py     # normal vs fraud plots -> docs/images/
```

Other files: `merchants.py` (places and shops), `simulate.py` (mixes honest traffic and attacks to hit `--fraud-rate`), `output.py` (Parquet: the 14 `Transaction` columns, then the ground-truth columns). The same seed gives a byte-identical file.
