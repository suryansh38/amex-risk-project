"""
Consolidates every module's output into clean, Power-BI-ready CSVs in
05_reporting/powerbi/extracts/. Power BI Desktop can't be scripted/built
headlessly from code (it's a GUI tool producing a binary .pbix), so this
script does the part that *can* be automated -- a stable, well-typed data
layer -- and BUILD_GUIDE.md walks through the remaining manual steps in
Power BI Desktop itself.

Run:
    python prepare_extracts.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
EXTRACTS_DIR = Path(__file__).resolve().parent / "extracts"


def copy_if_exists(src: Path, dst_name: str) -> None:
    if src.exists():
        pd.read_csv(src).to_csv(EXTRACTS_DIR / dst_name, index=False)
        print(f"  {dst_name}")
    else:
        print(f"  [skip] {dst_name} — run the upstream script that produces {src} first")


def main() -> None:
    EXTRACTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing extracts to {EXTRACTS_DIR}\n")

    copy_if_exists(ROOT / "04_portfolio_risk" / "output" / "book_summary.csv", "book_summary.csv")
    copy_if_exists(ROOT / "04_portfolio_risk" / "output" / "expected_loss_by_decile.csv", "expected_loss_by_decile.csv")
    copy_if_exists(ROOT / "04_portfolio_risk" / "output" / "stress_test_results.csv", "stress_test_results.csv")
    copy_if_exists(ROOT / "04_portfolio_risk" / "output" / "vintage_loss_curve.csv", "vintage_loss_curve.csv")
    copy_if_exists(ROOT / "02_credit_risk" / "python" / "output" / "scored_customers.csv", "credit_scored_customers.csv")
    copy_if_exists(ROOT / "02_credit_risk" / "python" / "output" / "feature_importance.csv", "credit_feature_importance.csv")
    copy_if_exists(ROOT / "03_fraud_risk" / "output" / "scored_transactions.csv", "fraud_scored_transactions.csv")
    copy_if_exists(ROOT / "03_fraud_risk" / "output" / "feature_importance.csv", "fraud_feature_importance.csv")

    print("\nOpen Power BI Desktop -> Get Data -> Folder -> point at this extracts/ directory,")
    print("or Get Data -> Text/CSV per file. See BUILD_GUIDE.md for the dashboard layout.")


if __name__ == "__main__":
    main()
