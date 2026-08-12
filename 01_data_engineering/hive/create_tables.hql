-- ============================================================
-- Hive DDL: external tables over raw + processed risk data.
-- Mirrors how a card issuer stages statement-level and
-- transaction-level data before it reaches a modeling layer.
-- Run with: hive -f create_tables.hql
-- (or via Beeline / Spark's HiveContext against the same warehouse)
-- ============================================================

CREATE DATABASE IF NOT EXISTS amex_risk;
USE amex_risk;

-- ------------------------------------------------------------
-- 1. Raw layer: schema-on-read external table over the
--    statement-level credit data (CSV, as downloaded/generated)
-- ------------------------------------------------------------
DROP TABLE IF EXISTS raw_credit_statements;
CREATE EXTERNAL TABLE raw_credit_statements (
    customer_id             STRING,
    balance                 DOUBLE,
    spend                   DOUBLE,
    payment_ratio           DOUBLE,
    delinquency_score       DOUBLE,
    utilization             DOUBLE,
    risk_score              DOUBLE,
    tenure_months           INT,
    target                  INT
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${hiveconf:raw_path}/credit_risk'
TBLPROPERTIES ('skip.header.line.count'='1');

-- ------------------------------------------------------------
-- 2. Raw layer: transaction-level data for fraud detection
-- ------------------------------------------------------------
DROP TABLE IF EXISTS raw_transactions;
CREATE EXTERNAL TABLE raw_transactions (
    v1 DOUBLE, v2 DOUBLE, v3 DOUBLE, v4 DOUBLE, v5 DOUBLE,
    v6 DOUBLE, v7 DOUBLE, v8 DOUBLE, v9 DOUBLE, v10 DOUBLE,
    txn_time    INT,
    amount      DOUBLE,
    is_fraud    INT
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${hiveconf:raw_path}/fraud_risk'
TBLPROPERTIES ('skip.header.line.count'='1');

-- ------------------------------------------------------------
-- 3. Curated layer: partitioned, columnar (Parquet) table that
--    the Spark ETL job (01_data_engineering/spark/etl_credit_risk.py)
--    writes into. This is what modeling notebooks actually read from
--    in a real pipeline -- never model off the raw CSV layer directly.
-- ------------------------------------------------------------
DROP TABLE IF EXISTS credit_risk_features;
CREATE EXTERNAL TABLE credit_risk_features (
    customer_id             STRING,
    balance                 DOUBLE,
    spend                   DOUBLE,
    payment_ratio           DOUBLE,
    delinquency_score       DOUBLE,
    utilization             DOUBLE,
    risk_score              DOUBLE,
    tenure_months           INT,
    spend_to_balance_ratio  DOUBLE,
    risk_tier               STRING,
    target                  INT
)
STORED AS PARQUET
LOCATION '${hiveconf:processed_path}/credit_risk_features';

-- ------------------------------------------------------------
-- Example analyst queries a risk analyst would actually run
-- against this warehouse -- included as a reference/demo.
-- ------------------------------------------------------------

-- Default rate by risk tier (sanity-check model segmentation)
-- SELECT risk_tier, COUNT(*) AS n, AVG(target) AS default_rate
-- FROM credit_risk_features
-- GROUP BY risk_tier
-- ORDER BY default_rate DESC;

-- Utilization vs. delinquency, decile-bucketed (feature exploration)
-- SELECT NTILE(10) OVER (ORDER BY utilization) AS util_decile,
--        AVG(delinquency_score) AS avg_delinquency,
--        AVG(target) AS default_rate,
--        COUNT(*) AS n
-- FROM credit_risk_features
-- GROUP BY NTILE(10) OVER (ORDER BY utilization);

-- Fraud rate by transaction amount bucket
-- SELECT CASE
--          WHEN amount < 50 THEN '<$50'
--          WHEN amount < 200 THEN '$50-200'
--          WHEN amount < 1000 THEN '$200-1000'
--          ELSE '$1000+'
--        END AS amount_bucket,
--        COUNT(*) AS n_txns,
--        SUM(is_fraud) AS n_fraud,
--        ROUND(AVG(is_fraud) * 100, 3) AS fraud_rate_pct
-- FROM raw_transactions
-- GROUP BY CASE
--          WHEN amount < 50 THEN '<$50'
--          WHEN amount < 200 THEN '$50-200'
--          WHEN amount < 1000 THEN '$200-1000'
--          ELSE '$1000+'
--        END
-- ORDER BY fraud_rate_pct DESC;
