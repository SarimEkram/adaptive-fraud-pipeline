#!/usr/bin/env sh
# Topics keyed by card_id; see docs/03. Run via `make topics`.
set -e
B="-X brokers=redpanda:9092"
rpk topic create transactions.scored     -p 6 -r 1 $B || true
rpk topic create labels.chargeback       -p 3 -r 1 $B || true
rpk topic create labels.analyst          -p 3 -r 1 $B || true
rpk topic create transactions.scored.dlq -p 1 -r 1 $B || true
rpk topic list $B
