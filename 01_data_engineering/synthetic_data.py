"""
Synthetic data generators used as a fallback across every module so the full
pipeline runs end-to-end even before real Kaggle data is downloaded.
Swap out for real data per docs/data_setup.md whenever you're ready.
"""
import numpy as np
import pandas as pd


def generate_credit_data(n_customers: int = 50_000, seed: int = 42) -> pd.DataFrame:
    """Mimics the shape of the Amex Default Prediction dataset: masked
    Delinquency (D_), Spend (S_), Payment (P_), Balance (B_), Risk (R_)
    features, one row per customer's latest statement, plus a binary target.
    """
    rng = np.random.default_rng(seed)

    balance = rng.gamma(shape=2.0, scale=1500, size=n_customers)
    spend = rng.gamma(shape=2.5, scale=800, size=n_customers)
    payment_ratio = rng.beta(a=2, b=2, size=n_customers)  # payment / statement balance
    delinquency_score = rng.beta(a=1.5, b=6, size=n_customers)  # higher = worse
    utilization = np.clip(balance / (balance.mean() * 2 + 1e-6), 0, 1.5)
    risk_score = rng.normal(loc=650, scale=80, size=n_customers)
    tenure_months = rng.integers(1, 240, size=n_customers)

    # target: logistic function of the risk drivers + noise, mimics real PD structure
    logit = (
        -4.0
        + 3.2 * delinquency_score
        + 1.4 * utilization
        - 2.0 * payment_ratio
        - 0.01 * (risk_score - 650) / 10
        - 0.002 * tenure_months
    )
    prob_default = 1 / (1 + np.exp(-logit))
    target = rng.binomial(1, prob_default)

    df = pd.DataFrame({
        "customer_ID": [f"CUST_{i:07d}" for i in range(n_customers)],
        "B_1_balance": balance.round(2),
        "S_1_spend": spend.round(2),
        "P_1_payment_ratio": payment_ratio.round(4),
        "D_1_delinquency_score": delinquency_score.round(4),
        "B_2_utilization": utilization.round(4),
        "R_1_risk_score": risk_score.round(1),
        "D_2_tenure_months": tenure_months,
        "target": target,
    })
    return df


def generate_fraud_data(n_transactions: int = 100_000, fraud_rate: float = 0.0017,
                         seed: int = 42) -> pd.DataFrame:
    """Mimics the Kaggle Credit Card Fraud dataset: anonymized PCA-style
    features (V1..V10), Time, Amount, and a highly imbalanced Class target.
    """
    rng = np.random.default_rng(seed)
    n_fraud = max(1, int(n_transactions * fraud_rate))
    n_normal = n_transactions - n_fraud

    normal = rng.normal(loc=0.0, scale=1.0, size=(n_normal, 10))
    fraud = rng.normal(loc=2.5, scale=2.2, size=(n_fraud, 10))  # shifted distribution

    features = np.vstack([normal, fraud])
    labels = np.array([0] * n_normal + [1] * n_fraud)

    amount = np.concatenate([
        rng.gamma(2.0, 60, n_normal),
        rng.gamma(1.2, 300, n_fraud),  # fraud skews to larger/erratic amounts
    ])
    time = rng.integers(0, 172_800, size=n_transactions)  # 48h window, seconds

    df = pd.DataFrame(features, columns=[f"V{i}" for i in range(1, 11)])
    df["Time"] = time
    df["Amount"] = amount.round(2)
    df["Class"] = labels
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)  # shuffle
    return df


if __name__ == "__main__":
    from pathlib import Path

    out = Path(__file__).resolve().parents[1] / "data" / "raw"
    (out / "credit_risk").mkdir(parents=True, exist_ok=True)
    (out / "fraud_risk").mkdir(parents=True, exist_ok=True)

    generate_credit_data().to_csv(out / "credit_risk" / "synthetic_train.csv", index=False)
    generate_fraud_data().to_csv(out / "fraud_risk" / "synthetic_transactions.csv", index=False)
    print(f"Synthetic data written to {out}")
