# gateway-sim

Plays three roles: merchants (normal spend), fraudsters (attack patterns), and the issuer (chargebacks arriving late).

| File | Role | Owner |
|---|---|---|
| customers.py | realistic customer population | **you write** |
| patterns.py | fraud attack patterns | **you write** |
| main.py | rate-controlled loop, sends to scoring, schedules chargebacks | Claude can help |
| control.py | small API the dashboard calls to launch attacks | Claude can help |

Phase 1 runs offline (`--out data/txns.parquet`); Phase 4 runs live.
