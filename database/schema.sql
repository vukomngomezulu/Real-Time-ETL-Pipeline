-- Real-Time Fraud Detection ETL Pipeline
-- Schema is intentionally minimal: every table here is actively read from
-- and written to by consumer/fraud_consumer.py and dashboard/app.py.

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id      UUID PRIMARY KEY,
    account_id           VARCHAR(20)   NOT NULL,
    account_holder        VARCHAR(100)  NOT NULL,
    amount                NUMERIC(12,2) NOT NULL,
    currency              VARCHAR(3)    NOT NULL DEFAULT 'ZAR',
    merchant_name          VARCHAR(150)  NOT NULL,
    merchant_category       VARCHAR(50)   NOT NULL,
    city                  VARCHAR(50)   NOT NULL,
    province               VARCHAR(50)   NOT NULL,
    transaction_type        VARCHAR(20)   NOT NULL,
    channel                VARCHAR(20)   NOT NULL,
    timestamp              TIMESTAMPTZ   NOT NULL,
    is_fraud_simulated      BOOLEAN       NOT NULL DEFAULT FALSE,
    fraud_score            NUMERIC(5,2),
    is_flagged             BOOLEAN       NOT NULL DEFAULT FALSE,
    flag_reasons            TEXT,
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_account   ON transactions(account_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
CREATE INDEX IF NOT EXISTS idx_transactions_flagged   ON transactions(is_flagged);
CREATE INDEX IF NOT EXISTS idx_transactions_city      ON transactions(city);

CREATE TABLE IF NOT EXISTS fraud_alerts (
    alert_id        SERIAL PRIMARY KEY,
    transaction_id   UUID NOT NULL REFERENCES transactions(transaction_id),
    fraud_score     NUMERIC(5,2) NOT NULL,
    reasons         TEXT NOT NULL,
    severity        VARCHAR(10) NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alerts_created ON fraud_alerts(created_at);
