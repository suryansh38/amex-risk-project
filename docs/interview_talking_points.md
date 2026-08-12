# Interview / Resume Talking Points

## One-line project summary (resume bullet)

> Built an end-to-end credit, fraud, and portfolio risk analytics pipeline
> on Amex's own default-prediction dataset — Hive/Spark ETL, XGBoost and
> logistic-regression scorecard models in Python/R, and Power BI/Excel
> reporting — modeling the analyst stack used in card-issuer risk teams.

## Why this project maps to Amex risk roles specifically

- **Used Amex's own released dataset** (the Kaggle Amex Default Prediction
  competition) rather than a generic credit dataset — shows you engaged
  with the actual problem the business has solved before, not a proxy.
- **Three separate risk types, not one flat pipeline** — mirrors how risk
  orgs are actually structured (credit risk, fraud, portfolio/strategy are
  different teams with different tools and different success metrics).
- **Two modeling approaches for the same problem** (XGBoost vs. a WOE/IV
  logistic scorecard) — lets you speak to the real tension in credit risk
  between predictive power and regulatory interpretability (Reg B
  adverse-action requirements are why card issuers still run scorecards
  alongside ML models, not instead of them).

## Questions this project prepares you to answer well

**"Walk me through a project on your resume."**
Use the pipeline diagram in the root README: raw data → Hive/Spark ETL →
modeling → reporting. Narrate it in that order — it demonstrates you think
in pipelines, not just models.

**"How would you handle class imbalance?"**
Point to `03_fraud_risk/train_fraud_model.py` — `class_weight="balanced"`
kept over naive oversampling deliberately, and PR-AUC used as the headline
metric instead of ROC-AUC, with the reasoning written in the script's
docstring. Be ready to explain *why* PR-AUC is more honest than ROC-AUC at
a 0.17% base rate.

**"How do you decide between a black-box model and a scorecard?"**
Use the Python vs. R module split: XGBoost for internal risk scoring where
interpretability constraints are looser; logistic scorecard for
adjudication decisions that need to be explainable to a customer or
regulator. Mention Information Value screening as the feature-selection
step that's specific to the scorecard approach.

**"How do you communicate risk to non-technical stakeholders?"**
Walk through the Power BI build guide's page structure — KPI cards first,
drill-down detail after — and the stress-testing page specifically. "Stress
EL Delta" as a single number is the kind of thing a risk committee actually
asks for; be ready to explain that instinct.

**"What's expected loss and how do you calculate it?"**
`04_portfolio_risk/expected_loss.R` — walk through EL = PD × EAD × LGD,
why LGD is assumed higher for high-PD segments, and how the stress
scenarios (1.5x / 2.3x PD multipliers) are structured like CCAR/DFAST
severely-adverse scenario design.

## Honest caveats to have ready (don't get caught overclaiming)

- The credit/fraud "raw" data is either the real Kaggle dataset (if you've
  downloaded it — see `docs/data_setup.md`) or a synthetic fallback with a
  similar statistical shape. Say clearly which one you actually ran it on.
- LGD, stress multipliers, and the vintage curve shape are reasonable
  industry-convention assumptions, not fitted to real charge-off data —
  be upfront that a production version would calibrate these from actual
  recovery and loss-timing data.
- The Spark/Hive layer runs locally (single-node), not against a real
  cluster — the value being demonstrated is correct pipeline *design*
  (partitioning, external tables, pandas-UDF batch scoring), not
  cluster-scale performance tuning.
