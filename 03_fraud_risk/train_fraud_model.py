"""
Fraud risk: transaction-level fraud classifier on a highly imbalanced
dataset (~0.17% fraud rate, matching the real Kaggle/ULB distribution).

Unlike the credit risk PD model, this optimizes for precision-recall
trade-off (not AUC alone) because the business cost is asymmetric: a
missed fraud costs far more than a false-positive decline, but too many
false positives erodes customer experience -- exactly the trade-off a
fraud risk analyst has to defend with a chosen operating threshold.

Run:
    python train_fraud_model.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score, precision_recall_curve, roc_auc_score, classification_report,
)

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "fraud_risk"
OUT_DIR = Path(__file__).resolve().parent / "output"


def load_transactions() -> pd.DataFrame:
    real = RAW_DIR / "creditcard.csv"
    synthetic = RAW_DIR / "synthetic_transactions.csv"
    if real.exists():
        return pd.read_csv(real)
    if synthetic.exists():
        return pd.read_csv(synthetic)

    sys.path.insert(0, str(ROOT / "01_data_engineering"))
    from synthetic_data import generate_fraud_data

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = generate_fraud_data()
    df.to_csv(synthetic, index=False)
    return df


def find_operating_threshold(y_true: np.ndarray, y_score: np.ndarray, min_precision: float = 0.5) -> float:
    """Pick the lowest score threshold that still clears a minimum
    precision bar -- mirrors how a fraud ops team sets a decline/review
    cutoff: maximize catch rate (recall) subject to a tolerable false-
    positive rate."""
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)
    eligible = precision[:-1] >= min_precision
    if not eligible.any():
        return float(thresholds[np.argmax(precision[:-1])])
    return float(thresholds[eligible][np.argmax(recall[:-1][eligible])])


def main() -> None:
    df = load_transactions()
    feature_cols = [c for c in df.columns if c not in ("Class",)]
    X = df[feature_cols]
    y = df["Class"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # class_weight="balanced" instead of naive resampling -- keeps the
    # real class distribution visible in evaluation, which matters when
    # reporting a realistic expected fraud-catch rate to the business
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba)
    ap = average_precision_score(y_test, proba)  # PR-AUC: the right headline metric for rare-event fraud

    threshold = find_operating_threshold(y_test.values, proba, min_precision=0.5)
    preds = (proba >= threshold).astype(int)

    print(f"ROC-AUC:        {auc:.4f}")
    print(f"PR-AUC (avg P): {ap:.4f}")
    print(f"Operating threshold (>=50% precision): {threshold:.4f}")
    print("\nClassification report at operating threshold:")
    print(classification_report(y_test, preds, target_names=["legitimate", "fraud"]))

    OUT_DIR.mkdir(exist_ok=True)
    importance = pd.Series(model.feature_importances_, index=feature_cols)
    importance.sort_values(ascending=False).to_csv(OUT_DIR / "feature_importance.csv")

    scored = X_test.copy()
    scored["actual_fraud"] = y_test.values
    scored["fraud_score"] = proba
    scored["flagged"] = preds
    scored.to_csv(OUT_DIR / "scored_transactions.csv", index=False)

    metrics = pd.DataFrame([{
        "roc_auc": auc, "pr_auc": ap, "operating_threshold": threshold, "n_test": len(y_test),
    }])
    metrics.to_csv(OUT_DIR / "model_metrics.csv", index=False)
    print(f"\nWrote scored_transactions.csv, feature_importance.csv, model_metrics.csv to {OUT_DIR}")


if __name__ == "__main__":
    main()
