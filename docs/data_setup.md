# Data Setup

## 1. Credit risk (core dataset)

**American Express — Default Prediction** (Kaggle competition data)
https://www.kaggle.com/competitions/amex-default-prediction/data

```bash
# requires: pip install kaggle, and a Kaggle API token at ~/.kaggle/kaggle.json
kaggle competitions download -c amex-default-prediction -p data/raw/credit_risk
cd data/raw/credit_risk && unzip amex-default-prediction.zip
```

Files you need:
- `train_data.csv` — customer profile/spend/payment/balance/risk features, one row per statement
- `train_labels.csv` — `customer_ID`, `target` (1 = defaulted within 120 days of latest statement)
- `test_data.csv` — for scoring (no labels; Kaggle holds these out)

The train file is large (~16GB uncompressed, wide feature set with masked
column names prefixed `D_`, `S_`, `P_`, `B_`, `R_` for Delinquency, Spend,
Payment, Balance, Risk). For local dev, sample it first:

```python
import pandas as pd
df = pd.read_csv("data/raw/credit_risk/train_data.csv", nrows=200_000)
df.to_csv("data/raw/credit_risk/train_sample.csv", index=False)
```

## 2. Fraud risk (extension dataset)

**Credit Card Fraud Detection** (Kaggle / ULB)
https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

```bash
kaggle datasets download -d mlg-ulb/creditcardfraud -p data/raw/fraud_risk
cd data/raw/fraud_risk && unzip creditcardfraud.zip
```

284,807 transactions, 492 fraud (0.17%) — PCA-anonymized features `V1`-`V28`,
plus `Time`, `Amount`, `Class` (target).

## 3. Portfolio risk

No separate download — `04_portfolio_risk/` consumes the *scored output* of
the credit risk model (predicted PD per customer) plus a synthetic exposure
(credit limit / balance) field to compute expected loss. See
`04_portfolio_risk/expected_loss.R`.

## No Kaggle account?

Both scripts fall back to a synthetic-data generator if the raw files aren't
found, so every module runs end-to-end without external downloads — useful
for testing the pipeline before you've pulled real data. Look for the
`if not raw_file.exists(): generate_synthetic(...)` branch at the top of each
entry-point script.
