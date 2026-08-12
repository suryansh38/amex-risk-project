"""
PySpark ETL: raw credit-statement CSV -> modeling-ready Parquet.

Demonstrates the layer that sits between Hive's raw external tables and
the modeling notebooks: type-safe cleaning, feature engineering, and a
partitioned Parquet write -- exactly what `credit_risk_features` in
01_data_engineering/hive/create_tables.hql points at.

Run:
    spark-submit etl_credit_risk.py
"""
import sys
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, Window

ROOT = Path(__file__).resolve().parents[2]
RAW_PATH = ROOT / "data" / "raw" / "credit_risk"
PROCESSED_PATH = ROOT / "data" / "processed" / "credit_risk_features"


def get_source_csv() -> Path:
    """Prefer real Kaggle data (train_data.csv + train_labels.csv joined
    upstream) if present; otherwise fall back to the synthetic generator
    so the ETL job is runnable without external downloads."""
    real = RAW_PATH / "train_sample.csv"
    synthetic = RAW_PATH / "synthetic_train.csv"
    if real.exists():
        return real
    if synthetic.exists():
        return synthetic

    sys.path.insert(0, str(ROOT / "01_data_engineering"))
    from synthetic_data import generate_credit_data

    RAW_PATH.mkdir(parents=True, exist_ok=True)
    generate_credit_data().to_csv(synthetic, index=False)
    return synthetic


def build_spark() -> SparkSession:
    return (
        SparkSession.builder
        .appName("amex-credit-risk-etl")
        .config("spark.sql.shuffle.partitions", "8")  # small local dev default
        .getOrCreate()
    )


def run_etl(spark: SparkSession, source_csv: Path) -> None:
    df = spark.read.csv(str(source_csv), header=True, inferSchema=True)

    # --- cleaning: cast, clip out-of-range values, null-handle -------------
    df = (
        df
        .withColumn("balance", F.greatest(F.col("B_1_balance").cast("double"), F.lit(0.0)))
        .withColumn("spend", F.greatest(F.col("S_1_spend").cast("double"), F.lit(0.0)))
        .withColumn("payment_ratio", F.col("P_1_payment_ratio").cast("double"))
        .withColumn("delinquency_score", F.col("D_1_delinquency_score").cast("double"))
        .withColumn("utilization", F.col("B_2_utilization").cast("double"))
        .withColumn("risk_score", F.col("R_1_risk_score").cast("double"))
        .withColumn("tenure_months", F.col("D_2_tenure_months").cast("int"))
        .withColumn("target", F.col("target").cast("int"))
        .na.fill({
            "payment_ratio": 0.0,
            "delinquency_score": 0.0,
            "utilization": 0.0,
        })
    )

    # --- feature engineering ------------------------------------------------
    df = df.withColumn(
        "spend_to_balance_ratio",
        F.when(F.col("balance") > 0, F.col("spend") / F.col("balance")).otherwise(F.lit(0.0)),
    )

    # risk tier via quantile-based scoring (mirrors how issuers bucket a
    # continuous internal risk score into decision-ready tiers)
    quantiles = df.approxQuantile("risk_score", [0.2, 0.5, 0.8], 0.01)
    q20, q50, q80 = quantiles
    df = df.withColumn(
        "risk_tier",
        F.when(F.col("risk_score") < q20, "High Risk")
         .when(F.col("risk_score") < q50, "Elevated Risk")
         .when(F.col("risk_score") < q80, "Standard")
         .otherwise("Prime"),
    )

    out_cols = [
        "customer_ID", "balance", "spend", "payment_ratio", "delinquency_score",
        "utilization", "risk_score", "tenure_months", "spend_to_balance_ratio",
        "risk_tier", "target",
    ]
    curated = df.select(*out_cols).withColumnRenamed("customer_ID", "customer_id")

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    curated.write.mode("overwrite").partitionBy("risk_tier").parquet(str(PROCESSED_PATH))

    print(f"Wrote {curated.count():,} rows to {PROCESSED_PATH}")
    curated.groupBy("risk_tier").agg(
        F.count("*").alias("n"),
        F.round(F.avg("target"), 4).alias("default_rate"),
    ).orderBy("default_rate", ascending=False).show()


if __name__ == "__main__":
    spark = build_spark()
    try:
        run_etl(spark, get_source_csv())
    finally:
        spark.stop()
