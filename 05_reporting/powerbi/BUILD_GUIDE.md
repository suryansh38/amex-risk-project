# Power BI Dashboard — Build Guide

Power BI Desktop is Windows-only and produces a binary `.pbix` file, so it
can't be built by a script here. This is the exact build to follow — treat
it as a checklist for a leadership-facing risk dashboard, the kind an Amex
risk manager would actually review weekly.

## 1. Connect data

`Get Data → Folder` → point at `05_reporting/powerbi/extracts/` (run
`prepare_extracts.py` first to populate it). Load each CSV as its own table.

## 2. Data model

Relationships (Model view):
- `credit_scored_customers[customer_id]` → link to `fraud_scored_transactions`
  only if you add a shared customer key (optional — the two modules are
  independent books in this project, so it's fine to leave them unrelated
  and use separate report pages).
- `expected_loss_by_decile[pd_decile]` is a standalone dimension table for
  the decile chart — no relationship needed.

## 3. DAX measures to add

```dax
Total Expected Loss = SUM(book_summary[total_expected_loss])

EL Rate % = DIVIDE([Total Expected Loss], SUM(book_summary[total_exposure]))

Fraud Catch Rate = 
    DIVIDE(
        CALCULATE(COUNTROWS(fraud_scored_transactions), fraud_scored_transactions[flagged] = 1, fraud_scored_transactions[actual_fraud] = 1),
        CALCULATE(COUNTROWS(fraud_scored_transactions), fraud_scored_transactions[actual_fraud] = 1)
    )

Stress EL Delta = 
    CALCULATE([Total Expected Loss], stress_test_results[scenario] = "Severe Recession (CCAR-style)")
    - CALCULATE([Total Expected Loss], stress_test_results[scenario] = "Baseline")
```

## 4. Pages

**Page 1 — Portfolio Overview**
- KPI cards: Total Exposure, Total Expected Loss, EL Rate %, Avg PD %
- Bar chart: Expected Loss by PD Decile (`expected_loss_by_decile`)
- Line chart: Cumulative Loss % by Month on Book (`vintage_loss_curve`) —
  the vintage curve

**Page 2 — Stress Testing**
- Clustered bar: Expected Loss by Scenario (`stress_test_results`)
- Card: Stress EL Delta (the DAX measure above) — the single number a
  risk committee actually asks for

**Page 3 — Credit Risk Model**
- Table: `credit_feature_importance`, sorted descending, as a horizontal
  bar chart — what's actually driving the PD model
- Scatter: predicted_pd vs. actual_default (from `credit_scored_customers`)
  to visually sanity-check calibration

**Page 4 — Fraud Risk**
- KPI cards: Fraud Catch Rate, Operating Threshold
- Table: top flagged transactions by fraud_score, filterable by Amount

## 5. Formatting

- Match the vault's navy accent (`#1A365D`) for headers/KPI cards — same
  palette used in `expected_loss_by_decile.png` from the R module, for
  visual consistency if you're presenting both together.
- Use card visuals with conditional formatting (red/amber/green) on EL
  Rate % and Fraud Catch Rate — this is standard risk-dashboard convention
  and is worth explicitly calling out in an interview as a design choice.

## 6. Refresh

Re-run `prepare_extracts.py` after any upstream model change, then
`Refresh` in Power BI — the whole chain (Hive/Spark → Python/R → Power BI)
is reproducible end to end, which is itself worth mentioning in an
interview as evidence of pipeline thinking, not just modeling.
