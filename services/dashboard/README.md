# dashboard

React + TypeScript (Vite). Built in Phase 6; Claude can carry most of the UI.

## Views

| View | Shows | Data source |
|---|---|---|
| Live feed | transactions streaming with action, score, latency | `WS /v1/live` |
| Transaction detail | features, reason codes, rules fired, shadow score | analyst-api |
| Review queue | REVIEW cases, fraud / legit buttons | `GET /v1/review-queue`, `POST .../label` |
| Attack console | launch each fraud pattern, start adaptive attacker | `POST /v1/attacks/{pattern}` |
| Thresholds | sliders showing approve/review/decline rates and expected cost | analyst-api |
| Model health | p99, PR-AUC over time, PSI per feature, champion vs challenger | Prometheus + analyst-api |

Design direction: an operations console for analysts, dense and calm; colour reserved for meaning (decline, review, drift), never decoration.

Scaffold when ready: `npm create vite@latest . -- --template react-ts`
