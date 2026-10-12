-- System of record. Every write is an idempotent upsert (failure mode F6).
-- Money is BIGINT cents (ADR-0007). Timestamps are TIMESTAMPTZ in UTC.

CREATE TABLE IF NOT EXISTS transactions (
    txn_id            UUID PRIMARY KEY,
    card_id           TEXT        NOT NULL,
    customer_id       TEXT        NOT NULL,
    amount_cents      BIGINT      NOT NULL CHECK (amount_cents > 0),
    currency          CHAR(3)     NOT NULL,
    merchant_id       TEXT        NOT NULL,
    mcc               CHAR(4)     NOT NULL,
    merchant_country  CHAR(2)     NOT NULL,
    lat               DOUBLE PRECISION NOT NULL,
    lon               DOUBLE PRECISION NOT NULL,
    channel           TEXT        NOT NULL,
    device_id         TEXT,
    event_time        TIMESTAMPTZ NOT NULL,
    ingested_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_txn_card_time ON transactions (card_id, event_time);
CREATE INDEX IF NOT EXISTS idx_txn_event_time ON transactions (event_time);

CREATE TABLE IF NOT EXISTS decisions (
    txn_id                UUID PRIMARY KEY REFERENCES transactions (txn_id),
    action                TEXT        NOT NULL CHECK (action IN ('APPROVE', 'REVIEW', 'DECLINE')),
    score                 REAL        NOT NULL,
    model_version         TEXT        NOT NULL,
    rules_fired           TEXT[]      NOT NULL DEFAULT '{}',
    reasons               JSONB       NOT NULL DEFAULT '[]',
    features              JSONB       NOT NULL,
    shadow_score          REAL,
    shadow_model_version  TEXT,
    latency_ms            REAL        NOT NULL,
    decided_at            TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dec_decided_at ON decisions (decided_at);

CREATE TABLE IF NOT EXISTS labels (
    txn_id      UUID        NOT NULL,
    source      TEXT        NOT NULL CHECK (source IN ('chargeback', 'analyst')),
    is_fraud    BOOLEAN     NOT NULL,
    labeled_at  TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (txn_id, source)
);

CREATE TABLE IF NOT EXISTS review_queue (
    txn_id       UUID PRIMARY KEY REFERENCES transactions (txn_id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at  TIMESTAMPTZ,
    reviewer     TEXT
);
CREATE INDEX IF NOT EXISTS idx_review_open ON review_queue (created_at) WHERE reviewed_at IS NULL;

CREATE TABLE IF NOT EXISTS model_versions (
    version       TEXT PRIMARY KEY,
    status        TEXT        NOT NULL CHECK (status IN ('trained', 'evaluated', 'shadow', 'promoted', 'rejected', 'retired')),
    metrics       JSONB       NOT NULL DEFAULT '{}',
    thresholds    JSONB       NOT NULL DEFAULT '{}',
    train_from    TIMESTAMPTZ,
    train_to      TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    promoted_at   TIMESTAMPTZ
);
