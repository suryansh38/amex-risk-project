"""
Spark batch scoring job: applies a trained fraud model at scale.

In production this is the piece that would run as a scheduled/streaming
Spark job against the live transaction stream (Structured Streaming from
Kafka in a real deployment); here it demonstrates the same pattern in
batch form -- broadcasting a trained sklearn model to workers via a
pandas UDF, which is the standard way to run row-wise Python ML inference
inside Spark without rewriting the model in Scala.

Run:
    spark-submit spark_scoring_job.py
Requires: train_fraud_model.py to have been run first (writes model via joblib)
"""
import sys
from pathlib import Path

import joblib
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import DoubleType

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "fraud_risk"
MODEL_PATH = Path(__file__).resolve().parent / "output" / "fraud_model.joblib"
SCORED_OUT = ROOT / "data" / "processed" / "fraud_scores"


def ensure_model_exists() -> None:
    """train_fraud_model.py doesn't persist the model by default (it's a
    single-script demo) -- retrain quickly and dump it here so this job
    is runnable standalone."""
    if MODEL_PATH.exists():
        return
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from train_fraud_model import load_transactions
    from sklearn.ensemble import RandomForestClassifier

    df = load_transactions()
    feature_cols = [c for c in df.columns if c != "Class"]
    model = RandomForestClassifier(n_estimators=200, max_depth=8, class_weight="balanced", random_state=42)
    model.fit(df[feature_cols], df["Class"])

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump({"model": model, "features": feature_cols}, MODEL_PATH)


def main() -> None:
    ensure_model_exists()
    bundle = joblib.load(MODEL_PATH)
    model, feature_cols = bundle["model"], bundle["features"]

    spark = SparkSession.builder.appName("amex-fraud-scoring").getOrCreate()

    source = RAW_DIR / "creditcard.csv"
    if not source.exists():
        source = RAW_DIR / "synthetic_transactions.csv"
    df = spark.read.csv(str(source), header=True, inferSchema=True)

    @pandas_udf(DoubleType())
    def score_batch(*cols: pd.Series) -> pd.Series:
        X = pd.concat(cols, axis=1)
        X.columns = feature_cols
        return pd.Series(model.predict_proba(X)[:, 1])

    scored = df.withColumn("fraud_score", score_batch(*[df[c] for c in feature_cols]))

    SCORED_OUT.parent.mkdir(parents=True, exist_ok=True)
    scored.write.mode("overwrite").parquet(str(SCORED_OUT))

    high_risk = scored.filter(scored.fraud_score >= 0.5).count()
    print(f"Scored {scored.count():,} transactions -> {SCORED_OUT}")
    print(f"{high_risk:,} flagged at >=0.5 fraud score")

    spark.stop()


if __name__ == "__main__":
    main()
