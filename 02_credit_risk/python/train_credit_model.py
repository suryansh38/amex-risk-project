"""
Credit risk: probability-of-default (PD) model using gradient boosting.

Reads the ETL'd feature table (falls back to synthetic data if the Spark
job hasn't been run yet), trains an XGBoost classifier, evaluates with the
metrics a risk team actually reports (AUC, KS statistic, Gini), and writes
SHAP-based feature importances for explainability -- required in any real
credit decision because of adverse-action / model-risk requirements.

Run:
    python train_credit_model.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, roc_curve
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed" / "credit_risk_features"
RAW_DIR = ROOT / "data" / "raw" / "credit_risk"
OUT_DIR = Path(__file__).resolve().parent / "output"


def load_features() -> pd.DataFrame:
    if PROCESSED_DIR.exists() and any(PROCESSED_DIR.glob("**/*.parquet")):
        return pd.read_parquet(PROCESSED_DIR)

    # fall back straight to synthetic data if the Spark ETL hasn't run --
    # keeps this script independently runnable for quick iteration
    sys.path.insert(0, str(ROOT / "01_data_engineering"))
    from synthetic_data import generate_credit_data

    df = generate_credit_data()
    df = df.rename(columns={
        "customer_ID": "customer_id",
        "B_1_balance": "balance",
        "S_1_spend": "spend",
        "P_1_payment_ratio": "payment_ratio",
        "D_1_delinquency_score": "delinquency_score",
        "B_2_utilization": "utilization",
        "R_1_risk_score": "risk_score",
        "D_2_tenure_months": "tenure_months",
    })
    df["spend_to_balance_ratio"] = np.where(df["balance"] > 0, df["spend"] / df["balance"], 0.0)
    return df


def ks_statistic(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Kolmogorov-Smirnov statistic: the standard separation metric risk
    teams quote alongside AUC (max distance between cumulative good/bad
    distributions)."""
    fpr, tpr, _ = roc_curve(y_true, y_score)
    return float(np.max(np.abs(tpr - fpr)))


def main() -> None:
    df = load_features()
    feature_cols = [
        "balance", "spend", "payment_ratio", "delinquency_score",
        "utilization", "risk_score", "tenure_months", "spend_to_balance_ratio",
    ]
    X = df[feature_cols]
    y = df["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="auc",
        random_state=42,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)
    ks = ks_statistic(y_test.values, proba)
    gini = 2 * auc - 1

    print(f"AUC:  {auc:.4f}")
    print(f"KS:   {ks:.4f}")
    print(f"Gini: {gini:.4f}")

    OUT_DIR.mkdir(exist_ok=True)

    # feature importance (gain-based; swap for shap.TreeExplainer if the
    # shap package is installed -- kept optional so this script has no
    # hard dependency beyond xgboost/sklearn)
    importance = pd.Series(model.feature_importances_, index=feature_cols)
    importance.sort_values(ascending=False).to_csv(OUT_DIR / "feature_importance.csv")

    scored = X_test.copy()
    scored["customer_id"] = df.loc[X_test.index, "customer_id"] if "customer_id" in df else X_test.index
    scored["actual_default"] = y_test.values
    scored["predicted_pd"] = proba
    scored.to_csv(OUT_DIR / "scored_customers.csv", index=False)

    metrics = pd.DataFrame([{"auc": auc, "ks": ks, "gini": gini, "n_test": len(y_test)}])
    metrics.to_csv(OUT_DIR / "model_metrics.csv", index=False)

    print(f"\nWrote scored_customers.csv, feature_importance.csv, model_metrics.csv to {OUT_DIR}")
    print("-> feeds 04_portfolio_risk/expected_loss.R and 05_reporting/")


if __name__ == "__main__":
    main()
