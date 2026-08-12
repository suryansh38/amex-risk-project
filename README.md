# Amex Risk Analytics Portfolio Project

A portfolio project built to demonstrate the analytical stack used in credit-card
risk management roles at American Express: **credit risk modeling, fraud
detection, and portfolio risk reporting**, executed across the tools these roles
actually use — Hive, Spark, Python, R, Excel, and Power BI.

## Why this shape

Amex risk roles (Risk Analyst, Decision Science Analyst, Risk Management
Associate) split into three recurring problem types. This project builds one
module per type instead of one flat pipeline, because each type is scored and
communicated differently in the real job:

| Module | Business question | Primary tools |
|---|---|---|
| **Credit Risk** (core) | Will this customer default in the next 12 months? | Python (XGBoost/Logistic), R (scorecard/GLM) |
| **Fraud Risk** (extension) | Is this transaction fraudulent, in near real time? | Python (imbalanced classification), Spark |
| **Portfolio Risk** (extension) | What's our expected loss / loss under stress, at the book level? | R, Excel, Power BI |

Data engineering (Hive + Spark) underpins all three: it's the ingestion/ETL
layer that turns raw transaction and account data into modeling-ready tables,
exactly as it would sit upstream of a risk model at a card issuer.

## Pipeline

```
raw data (Kaggle: Amex Default Prediction)
        │
        ▼
01_data_engineering/  — Hive DDL (schema-on-read) + PySpark ETL
        │              (aggregation, feature engineering at scale)
        ▼
02_credit_risk/        — Python: gradient-boosted PD model
                          R: logistic regression scorecard (interview-standard)
        │
        ├──▶ 03_fraud_risk/     — transaction-level anomaly/fraud classifier
        │
        └──▶ 04_portfolio_risk/ — expected loss, vintage curves, stress testing
                        │
                        ▼
        05_reporting/  — Excel workbook (analyst-facing)
                          Power BI dashboard (leadership-facing)
```

## Dataset

**Primary**: [American Express — Default Prediction](https://www.kaggle.com/competitions/amex-default-prediction)
(Kaggle). This is Amex's own released dataset — anonymized customer profile
and payment/balance/spend features, with a binary 12-month default target.
Using it directly is a credible, citable choice for an Amex-facing portfolio
piece.

**Extension dataset (fraud module)**: [Credit Card Fraud Detection](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud)
(Kaggle/ULB) — transaction-level, highly imbalanced, standard benchmark for
fraud classification.

Download both into `data/raw/` (not committed to git — see `.gitignore`).
See [docs/data_setup.md](docs/data_setup.md) for exact steps.

## Repo structure

```
amex-risk-project/
├── data/
│   ├── raw/                 # downloaded, untouched (gitignored)
│   └── processed/           # ETL output, modeling-ready (gitignored)
├── 01_data_engineering/
│   ├── hive/                 # DDL: external tables over raw data
│   └── spark/                # PySpark ETL: clean, aggregate, engineer features
├── 02_credit_risk/
│   ├── python/                # XGBoost PD model, SHAP explainability
│   └── r/                     # logistic regression scorecard + WOE binning
├── 03_fraud_risk/             # Python: imbalanced classification, Spark scoring
├── 04_portfolio_risk/         # R: expected loss, vintage analysis, stress test
├── 05_reporting/
│   ├── excel/                 # analyst workbook (formulas + pivot-ready extracts)
│   └── powerbi/                # Power BI data extracts + build guide
└── docs/
    ├── data_setup.md
    └── interview_talking_points.md
```

## Status

Scaffolding + working starter scripts in place for every module. Fill in as
you work through it — see `docs/` for setup and the resume/interview framing.
