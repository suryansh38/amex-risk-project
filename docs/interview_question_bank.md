# Interview Question Bank — Risk Analytics Roles

An exhaustive, categorized question-and-answer set for credit risk / fraud
risk / portfolio risk analyst interviews (Amex and similar card issuers,
NBFCs, banks). Every answer is written to be spoken out loud in an
interview, grounded in the actual code in this repo where relevant.

General questions (SQL, stats, ML fundamentals) reflect standard industry
knowledge. Amex-specific and RBI-specific claims are sourced — see
`docs/interview_talking_points.md` and `docs/regulatory_context.md` for the
citation trail behind those.

---

## A. SQL

**Q: Write a query to find each customer's most recent statement balance.**
A: Classic "latest row per group" problem —
```sql
SELECT customer_id, balance, statement_date
FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY statement_date DESC) AS rn
  FROM statements
) t
WHERE rn = 1;
```
`ROW_NUMBER()` with `PARTITION BY` is the standard tool for "top-N per group" — know this pattern cold, it comes up constantly.

**Q: What's the difference between `WHERE` and `HAVING`?**
A: `WHERE` filters rows before grouping/aggregation happens; `HAVING` filters groups after aggregation. You can't write `WHERE COUNT(*) > 5` because `COUNT` doesn't exist yet at the row level — that's what `HAVING` is for.

**Q: Explain `INNER JOIN` vs `LEFT JOIN` with a risk-data example.**
A: An `INNER JOIN` between `customers` and `defaults` only returns customers who actually appear in both tables — if you want "all customers, and their default status if any," you need a `LEFT JOIN` from `customers`, or you'll silently lose every customer who never defaulted (they just wouldn't exist in an inner-joined result).

**Q: How would you find customers whose utilization increased for 3 consecutive months?**
A: Window functions — `LAG(utilization) OVER (PARTITION BY customer_id ORDER BY month)` to compare each month to the previous one, flag increases, then a running count (or `LAG`/`LEAD` chained) to check 3 in a row. This is the kind of "sequential pattern" question that tests whether you reach for window functions instead of self-joins.

**Q: What's a window function, and why use one instead of `GROUP BY`?**
A: `GROUP BY` collapses rows into one row per group. A window function (`OVER (PARTITION BY ... ORDER BY ...)`) computes an aggregate *without* collapsing rows — you keep every original row, but each one also knows things like its rank, running total, or the previous row's value within its group. Essential whenever you need both the detail row and a group-level calculation side by side.

**Q: Query: monthly default rate trend.**
A:
```sql
SELECT DATE_TRUNC('month', statement_date) AS month,
       AVG(CAST(target AS FLOAT)) AS default_rate,
       COUNT(*) AS n
FROM credit_risk_features
GROUP BY 1
ORDER BY 1;
```
`AVG` of a 0/1 column is a fast, common trick for a rate — it's literally "% of rows where target=1."

**Q: How do you handle NULLs in an aggregate?**
A: Most aggregate functions (`AVG`, `SUM`, `COUNT(column)`) silently ignore NULLs — which can quietly bias a rate calculation if NULLs aren't actually "0" or "missing at random." Always ask *why* a value is NULL before aggregating past it; `COALESCE(column, 0)` forces a decision instead of a silent skip.

**Q: What's a CTE and why prefer it over a subquery?**
A: A `WITH x AS (...)` common table expression — functionally similar to a subquery, but named and readable top-to-bottom, and reusable multiple times in the same query without repeating the logic. Prefer it any time a query has more than one logical "step."

**Q: How would you detect duplicate customer records?**
A:
```sql
SELECT customer_id, COUNT(*)
FROM customers
GROUP BY customer_id
HAVING COUNT(*) > 1;
```
Basic `GROUP BY … HAVING COUNT(*) > 1` — the fundamental duplicate-detection pattern, worth having reflexively ready.

**Q: Explain query execution order (conceptually).**
A: Not the order you *write* it in — actual logical order is roughly: `FROM` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `ORDER BY` → `LIMIT`. This is why you can't reference a `SELECT` alias inside `WHERE` (it doesn't exist yet at that stage) but you often can in `ORDER BY` (it exists by then).

---

## B. Statistics & Probability

**Q: Explain Bayes' theorem with a fraud-detection example.**
A: P(fraud | flagged) ≠ P(flagged | fraud). If fraud is 0.17% of transactions and your model correctly flags 90% of real fraud but also wrongly flags 5% of legitimate ones, most flagged transactions are still *not* fraud — because there are so many more legitimate transactions to draw false positives from. Bayes' theorem formalizes this: P(fraud|flagged) = [P(flagged|fraud)×P(fraud)] / P(flagged). This is precisely why precision, not just recall, matters at low base rates.

**Q: What's the Central Limit Theorem, and why does it matter for risk reporting?**
A: The average of many independent samples tends toward a Normal distribution, regardless of the underlying data's own shape, as sample size grows. It's why you can build confidence intervals around an average default rate estimated from a large portfolio even though individual customer outcomes are binary (default/no default), not Normal at all.

**Q: What's a p-value, in plain terms?**
A: The probability of seeing data this extreme (or more) *if* there were actually no real effect. A small p-value doesn't prove your effect is real or large — it just means the pattern is unlikely to be pure noise, assuming your test's other assumptions hold.

**Q: Type I vs. Type II error — give a credit risk example.**
A: Type I (false positive): declining a customer who would actually have paid back fine — a lost-revenue error. Type II (false negative): approving a customer who then defaults — a credit-loss error. Every cutoff decision (see KS discussion) is a trade-off between these two error types; there's no cutoff that minimizes both simultaneously.

**Q: What's the difference between correlation and causation? Give a risk example.**
A: High card spend correlates with lower default — but that's likely because financially healthy customers both spend more *and* default less (a common cause), not because spending itself prevents default. Acting on this correlation (e.g., raising limits purely to "cause" lower risk) would be a mistake — a classic confounding-variable trap.

**Q: Explain the difference between a Normal and a Gamma distribution, and why it matters for modeling balances/spend.**
A: Normal is symmetric around a mean; real financial quantities like balance or spend are usually right-skewed — most customers cluster low, with a long tail of high-value outliers, which Gamma captures naturally (see this project's `synthetic_data.py`, which deliberately uses Gamma, not Normal, for exactly this reason).

**Q: What is variance, and what does a high-variance model mean practically?**
A: Variance measures how much a model's predictions would change if trained on a slightly different sample of the same population. A high-variance model (e.g., a very deep single decision tree) fits its specific training data closely but swings wildly on new data — the textbook definition of overfitting.

**Q: Explain the bias-variance trade-off.**
A: Bias = error from a model being too simple to capture the real pattern (underfitting). Variance = error from a model being so flexible it fits noise in the training data (overfitting). Total error is roughly bias² + variance + irreducible noise — model tuning (like XGBoost's `max_depth`) is largely about finding the sweet spot between the two.

**Q: What's a confidence interval, and how would you explain "95% confidence" correctly?**
A: If you repeated the same sampling process many times and built a 95% CI each time, 95% of those intervals would contain the true value. It is *not* "there's a 95% chance the true value is in this specific interval" — a common, technically wrong phrasing worth avoiding in an interview.

**Q: How would you test whether a new risk score is actually better than the old one?**
A: Compare AUC/KS/Gini on the same held-out test set for both scores; ideally also run a formal statistical test (e.g., DeLong's test for comparing two ROC-AUCs) rather than just eyeballing a small numeric difference, since a marginal AUC improvement can be noise rather than a real gain.

---

## C. Machine Learning / Modeling

**Q: Walk through how XGBoost works.**
A: Start from a simple baseline prediction (e.g., the average default rate). Build a small, shallow decision tree whose job is to predict the *errors* the current prediction is making. Add that tree's correction (scaled down by a learning rate) to the running prediction. Repeat for hundreds of trees, each one correcting what's still wrong after all the previous ones. Final prediction is the sum of the baseline plus every tree's small correction — see [pipeline_deep_dive Stage D](#) for the code-level walkthrough already built for this project.

**Q: Why use shallow trees in boosting instead of one deep tree?**
A: A single deep tree can memorize training data via thousands of hyper-specific splits (overfitting). Boosting's power comes from combining many *weak*, shallow learners, each catching a small, general pattern — an ensemble of simple models generalizes better than one complex model.

**Q: What's the difference between bagging (Random Forest) and boosting (XGBoost)?**
A: Bagging trains many trees independently and in parallel on random subsamples, then averages their votes — it reduces variance. Boosting trains trees sequentially, each one specifically targeting the previous ensemble's errors — it reduces bias (and can reduce variance too, with proper regularization). This project actually uses both: Random Forest (bagging) for fraud, XGBoost (boosting) for credit risk — worth naming that distinction explicitly if asked why.

**Q: Why would you choose logistic regression over XGBoost for some use cases?**
A: Interpretability and regulatory defensibility — logistic regression gives one clear coefficient per feature, so you can say precisely how each factor moves the odds of default, which is required for adverse-action explanations under lending regulation. XGBoost's hundreds of interacting trees can't be summarized that cleanly, even with tools like SHAP.

**Q: What is overfitting, and how do you detect it?**
A: The model performs well on training data but poorly on unseen data — it learned noise/specifics of the training set rather than the general pattern. Detected by comparing train vs. test performance: a big gap (e.g., 95% train AUC, 65% test AUC) is the signature. Fixed via simpler models, regularization, more data, or early stopping.

**Q: Explain precision, recall, F1, and when each matters most.**
A: Precision = of what you flagged positive, how much was actually positive. Recall = of all real positives, how much did you catch. F1 is their harmonic mean, useful when you need one number balancing both. In fraud, recall often matters more early (catch the fraud) constrained by a precision floor (don't overwhelm ops) — see this project's `find_operating_threshold` function, which encodes exactly that trade-off.

**Q: What is cross-validation, and why not just use a single train/test split?**
A: K-fold cross-validation splits the data into K parts, trains on K-1 and tests on the remaining 1, rotating through all K combinations — giving a more stable estimate of model performance than a single split, which can be lucky or unlucky depending on which rows happened to land in the test set.

**Q: How do you handle missing data in a model?**
A: Depends on *why* it's missing. If missing-not-at-random (e.g., a field only populated for approved applications), imputing it naively can leak information or bias the model. Common approaches: median/mode imputation for MAR data, a separate "missing" flag/category so the model can use missingness itself as a signal, or tree-based models (like XGBoost) which can handle missing values natively via learned split directions.

**Q: What is feature importance, and what are its limitations?**
A: A ranking of how much each feature contributed to the model's predictions (e.g., gain-based importance in XGBoost). Limitation: it doesn't show *direction* (does higher utilization increase or decrease risk — importance alone can't say), and correlated features can split credit for the same signal, making both look less important than the underlying pattern actually is. SHAP values fix the direction problem.

**Q: What's SHAP, and why would a risk team use it?**
A: SHAP (SHapley Additive exPlanations) attributes each individual prediction to a specific contribution from each feature, borrowed from cooperative game theory. Unlike global feature importance, SHAP explains *this specific customer's* score — useful for both model debugging and (with care) individual-level explainability discussions, though it's still not as legally clean as a scorecard's WOE bins.

**Q: How would you monitor a deployed credit model over time?**
A: Track population stability (has the incoming customer population's feature distributions drifted from training?), score-to-outcome calibration over time (are predicted PDs still matching actual default rates?), and periodic AUC/KS on fresh outcome data — a model that was good at launch can silently degrade as the economy or customer base shifts.

**Q: What is regularization, and why does XGBoost need it?**
A: A penalty added to the training objective that discourages overly complex models (e.g., L1/L2 penalties on tree leaf weights in XGBoost). Without it, boosting can keep adding trees that increasingly fit training noise — regularization keeps the model from getting there.

**Q: Explain the ROC curve construction from scratch.**
A: Rank every observation by predicted score. At every possible cutoff, compute the true positive rate (recall) and false positive rate. Plot TPR (y-axis) against FPR (x-axis) as the cutoff sweeps from "flag everyone" to "flag no one." The area under that curve is AUC.

---

## D. Credit Risk Domain

**Q: What is Probability of Default (PD)?**
A: The likelihood, over a defined horizon (commonly 12 months), that a borrower fails to meet their obligations — the core output of the credit model in this project (`predicted_pd` in `02_credit_risk/python/output/scored_customers.csv`).

**Q: Define EAD and LGD, and how they combine with PD.**
A: EAD (Exposure At Default) — how much is actually owed/at risk if default happens (approximated as current balance here). LGD (Loss Given Default) — what fraction of that exposure is actually lost after recovery/collections. Expected Loss = PD × EAD × LGD — see `04_portfolio_risk/expected_loss.R`.

**Q: Why is LGD higher for credit cards than for mortgages?**
A: Credit cards are unsecured — there's no asset to repossess on default, so recovery relies entirely on collections, keeping LGD high (65–75% is a standard assumption). Mortgages are secured by the property, so the lender can recover much of the loan by foreclosing, keeping LGD much lower.

**Q: What is a scorecard, and why do banks still use them alongside ML?**
A: A points-based model (built via WOE-binned logistic regression) that converts risk factors into an explainable, auditable score. Used because adverse-action regulation requires lenders to give specific, defensible reasons for declining an applicant — something a scorecard's bins can do cleanly and a black-box ML ensemble generally can't. See `02_credit_risk/r/scorecard_model.R`.

**Q: What's the difference between application scoring and behavioral scoring?**
A: Application scoring predicts risk for a *new* applicant using only what's known at origination (income, bureau data, stated purpose). Behavioral scoring predicts risk for an *existing* customer using their actual account behavior (payment history, utilization trend, recent delinquency) — generally far more predictive, since it's observed rather than self-reported.

**Q: What is a vintage curve, and why does it matter?**
A: A chart of cumulative loss (or default rate) plotted against months-on-book for a cohort of accounts originated in the same period. It typically ramps up, peaks (often 12–18 months in for unsecured credit), then decays — used to compare whether a *new* origination cohort is performing better or worse than historical cohorts at the same age. See `vintage_loss_curve` in `04_portfolio_risk/expected_loss.R`.

**Q: What drives profitability in a credit card business?**
A: Interchange fees (paid by merchants), interest income on revolving balances, and annual fees — offset against rewards costs, funding costs, operating costs, and credit losses. A risk team's job is fundamentally about protecting the gap between the first group and credit losses in the second.

**Q: What is utilization, and why is it predictive of default?**
A: The fraction of available credit currently in use. High utilization is one of the strongest standard predictors of default — it signals financial stress (relying heavily on credit) and reduces the buffer a customer has for unexpected expenses, both of which independently raise default risk.

**Q: How would you decide whether to raise a customer's credit limit?**
A: Balance expected revenue uplift (more spend, more interchange/interest) against the incremental expected loss from higher EAD if they do default — essentially a mini expected-loss calculation on the *marginal* limit increase, plus behavioral signals (recent delinquency, utilization trend) that would flag the increase as risky regardless of the raw PD.

**Q: What's the difference between a "hard" and "soft" credit inquiry, and why does it matter for risk modeling?**
A: A hard inquiry (e.g., applying for new credit) can slightly lower a bureau score and signals active credit-seeking behavior — often used as a risk feature itself ("recent hard inquiries" correlates with financial stress). A soft inquiry (e.g., a pre-approval check) doesn't affect the score and isn't visible to other lenders.

---

## E. Fraud & Imbalanced Data

**Q: Why is accuracy a bad metric for fraud detection?**
A: With fraud at ~0.17% of transactions, predicting "not fraud" on everything scores 99.83% accuracy while catching zero fraud — the metric is meaningless at this base rate. Use precision, recall, and PR-AUC instead.

**Q: Why choose `class_weight="balanced"` over oversampling techniques like SMOTE?**
A: `class_weight="balanced"` tells the loss function to penalize errors on the rare class more heavily, without inventing synthetic rows — keeping the evaluation set's real-world class distribution intact, which matters when you need a realistic estimate of the actual fraud-catch rate at deployment. SMOTE can also work well, but risks generating unrealistic synthetic fraud patterns if not applied carefully.

**Q: What is PR-AUC, and why prefer it over ROC-AUC for rare events?**
A: PR-AUC summarizes the precision/recall trade-off across all thresholds, the same way ROC-AUC summarizes TPR/FPR. At very low base rates, ROC-AUC can look deceptively good because the false positive *rate* stays low even with many false positives in absolute terms (since the negative class is huge) — PR-AUC is more sensitive to this and gives an honester picture.

**Q: How would you choose an operating threshold for a fraud model?**
A: Based on a business constraint, not a statistical default like 0.5 — e.g., "the lowest threshold that still keeps precision above 50%" (as implemented in `find_operating_threshold` in this project), balancing fraud caught against how many legitimate customers get needlessly flagged and the operational cost of reviewing them.

**Q: What are false positives and false negatives worth in fraud, respectively?**
A: A false negative (missed fraud) costs the actual fraudulent transaction amount plus potential chargeback/reputation costs. A false positive (legit transaction flagged) costs customer friction, potential churn, and manual review labor — asymmetric, and the "right" threshold depends on the relative size of these costs, which is a business decision, not a purely statistical one.

**Q: What are Early Warning Signals (EWS) and Red Flagging of Accounts (RFA)?**
A: Regulatory concepts (RBI Master Directions on Fraud Risk Management, 2024) — EWS are indicators (unusual transaction patterns, sudden change in behavior) that trigger closer monitoring *before* fraud is confirmed; RFA is the formal flagging of an account under investigation, which carries its own governance and reporting obligations. See `docs/regulatory_context.md`.

**Q: How would you detect a new fraud pattern the model wasn't trained on?**
A: Models trained on historical fraud can miss novel patterns (concept drift). Complementary approaches: unsupervised anomaly detection (flagging transactions statistically unlike anything seen before, not just unlike known fraud), rule-based EWS layered on top of the ML model, and regular retraining on fresh confirmed-fraud labels.

**Q: What's the difference between supervised fraud detection and anomaly detection, and when would you use each?**
A: Supervised (this project's `RandomForestClassifier`) needs labeled historical fraud examples and learns "what past fraud looked like" — strong when fraud patterns are relatively stable and labels are available. Anomaly detection needs no fraud labels at all, flagging anything statistically unusual — better for catching genuinely novel fraud types, at the cost of more false positives since "unusual" isn't the same as "fraudulent."

---

## F. Data Engineering — Spark / Hive / ETL

**Q: What is ETL, and where does it fit in a risk pipeline?**
A: Extract (read raw data), Transform (clean and reshape it), Load (write the result somewhere usable). In this project: Extract reads the raw CSV, Transform is the Spark script's cleaning/feature-engineering logic, Load writes to a local Parquet folder standing in for a real warehouse table.

**Q: Why Spark instead of pandas for large-scale data processing?**
A: Pandas loads everything into a single machine's memory — it breaks at a scale that easily fits within a Spark cluster's distributed memory across many machines. The same Spark transformation code, unchanged, scales from a laptop sample to billions of rows.

**Q: What's the difference between Hive and Spark?**
A: Hive is a SQL-like query and metadata-cataloging layer over data sitting in a distributed file system (originally Hadoop) — it describes data shape and lets you query it with familiar SQL syntax. Spark is a general-purpose distributed compute engine that can do far more than query — cleaning, joining, running ML — and commonly reads from/writes to Hive-cataloged tables as its data source/sink.

**Q: What's an `EXTERNAL TABLE` in Hive, and why does it matter?**
A: An external table only stores Hive's *metadata* about where data lives and its schema — the underlying files aren't owned or moved by Hive. Dropping an external table doesn't delete the data; dropping a *managed* table does. External tables are the safer default when other systems also need access to the same files.

**Q: What is a partition in Spark/Hive, and why partition by risk tier or date?**
A: Physically splitting stored data into separate folders/files by a column's value (e.g., `risk_tier=Prime/`, `risk_tier=High Risk/`). Queries that filter on that column (e.g., "just show me High Risk accounts") only need to read the relevant partition's files, not the whole dataset — a major performance win at scale.

**Q: What's a pandas UDF in Spark, and why use one?**
A: A way to run ordinary Python/pandas/sklearn code inside a distributed Spark job — Spark hands each worker a chunk of rows as a pandas DataFrame, your Python function processes that chunk, Spark reassembles the results. Lets you apply an existing trained Python model (like this project's fraud classifier) across a huge dataset without rewriting it in Scala. See `03_fraud_risk/spark_scoring_job.py`.

**Q: What would you check first if a Spark ETL job produced unexpected row counts?**
A: Whether a join changed cardinality unexpectedly (e.g., an accidental one-to-many join silently duplicating rows), whether a filter condition on nullable columns dropped more than intended (NULL comparisons don't behave like you'd expect in SQL-style filters), and whether upstream data itself changed shape.

**Q: How would you productionize this batch ETL into something that runs on a schedule?**
A: Wrap it in an orchestrator (e.g., Airflow) that triggers the Spark job on a schedule or on new-file arrival, add data-quality checks between stages (row count sanity checks, null-rate thresholds) that halt the pipeline on failure rather than silently propagating bad data, and version the output tables so a bad run can be rolled back.

**Q: What would change if data needed to be scored in real time instead of batch?**
A: Replace the file-based Extract with a Kafka consumer, and replace the batch Spark job with Spark Structured Streaming (or an equivalent) scoring each event as it arrives within milliseconds — the model logic itself doesn't need to change, just how data flows into it. (This project only implements the batch form — worth being upfront about that distinction if asked.)

**Q: Why cast/clean types explicitly in the Spark ETL step instead of trusting the source file?**
A: Source CSVs from upstream systems often have inconsistent types (numbers stored as strings, unexpected blanks) — explicit casting fails loudly and predictably if the source format changes, rather than silently propagating wrong types (e.g., a numeric column read as string, breaking every downstream numeric operation) deep into the pipeline where it's much harder to trace.

---

## G. R / Scorecards / WOE-IV

**Q: What is Weight of Evidence (WOE)?**
A: For a binned feature, WOE for a bin = log(% of good customers in that bin ÷ % of bad customers in that bin). It re-expresses a raw feature value as "how much safer or riskier is this bucket relative to average," on a scale that plugs directly and linearly into logistic regression.

**Q: What is Information Value (IV), and what do the standard thresholds mean?**
A: IV sums each bin's WOE weighted by the difference in good/bad proportions — a single number scoring how predictive a whole feature is. Convention: <0.02 useless, 0.02–0.1 weak, 0.1–0.3 medium, 0.3+ strong. Used to screen features before modeling, computed directly from data without needing to fit anything first.

**Q: Why binning instead of using continuous variables directly in a scorecard?**
A: Binning captures non-linear relationships (e.g., risk might not rise smoothly with age — it could be U-shaped) without needing polynomial terms, handles outliers naturally (they just fall in the extreme bin), and produces interpretable, auditable buckets ("utilization 40–60% → +15 points") instead of an opaque coefficient on a raw number.

**Q: How do you convert a logistic regression into a points-based score?**
A: Pick a base score and base odds (e.g., 660 points at odds of 1:19), and a PDO (points-to-double-odds, e.g., 40) defining how many points it takes to halve the odds of default. Each WOE-binned coefficient is then rescaled into a points allocation using these anchors — the same mechanism that produces a real bureau score.

**Q: How would you validate a scorecard's stability over time?**
A: A Population Stability Index (PSI) comparing the score distribution at build-time against the current live population — a PSI above ~0.25 typically signals the population has drifted enough that the scorecard needs review or rebuilding.

**Q: Why might a scorecard underperform a gradient-boosted model, and why accept that trade-off anyway?**
A: Logistic regression assumes a linear (in log-odds) relationship between binned features and outcome, and can't automatically capture complex feature interactions the way tree ensembles do — so it typically shows a lower AUC/KS. Banks accept this gap for the *adjudication* decision because the interpretability is a regulatory requirement, not optional — see the WOE/IV entry above and `docs/regulatory_context.md`.

---

## H. Portfolio Risk — Expected Loss / Stress Testing

**Q: Write out the Expected Loss formula and define each term.**
A: EL = PD × EAD × LGD. PD: probability of default over the horizon. EAD: exposure at default (how much is owed if it happens). LGD: loss given default (the fraction of that exposure not recovered). See `04_portfolio_risk/expected_loss.R`.

**Q: What's the difference between Expected Loss and Unexpected Loss?**
A: Expected Loss is the average loss a portfolio should experience in a normal year — it's priced into interest rates/fees and covered by provisions. Unexpected Loss is the additional loss beyond that average in a bad year — covered by capital reserves, not pricing, which is exactly what stress testing and capital adequacy requirements are designed around.

**Q: What is stress testing, and how does CCAR/DFAST work conceptually?**
A: Applying a hypothetical severe macroeconomic scenario (high unemployment, falling asset prices, market shock) to the current portfolio to see how much worse losses would get, and whether the institution would still have enough capital to survive it. CCAR/DFAST is the U.S. Federal Reserve's real annual version of this for large banks; this project's `stress_test_results.csv` mimics the concept with simplified PD multipliers.

**Q: Why does a stress scenario multiply PD rather than directly setting a new loss number?**
A: Because the underlying mechanism of a recession is that default probability rises (job losses, income shocks) — multiplying PD keeps the stress mechanistically tied to the same EL formula used in the baseline case, rather than an arbitrary top-down loss guess, making the scenario auditable and consistent.

**Q: What is a vintage curve used for in capital planning?**
A: Comparing how a new cohort of originations is tracking against historical loss curves at the same age lets a portfolio team catch underwriting deterioration early — if a new vintage is running hotter than history at month 6, that's a signal worth investigating well before the full lifetime loss is realized.

**Q: How would you explain "Stress EL Delta" to a non-technical risk committee?**
A: "If a moderate-to-severe recession hit today, here's how many additional rupees/dollars of losses we'd expect beyond our normal baseline" — a single number translating a statistical scenario into a budget-relevant figure, which is exactly the kind of translation a risk committee actually wants (see the Power BI DAX measure of the same name in `05_reporting/powerbi/BUILD_GUIDE.md`).

**Q: What's the difference between provisioning and capital?**
A: Provisions are an accounting reserve set aside against *expected* losses, reducing reported profit now. Capital is the buffer held against *unexpected* losses beyond what's provisioned — a solvency cushion, not an accounting entry. The RBI's new ECL framework (see next section) primarily changes how provisions are calculated, but has capital-ratio implications too (estimated ~120bps CET-1 impact industry-wide).

**Q: How would you explain why Stage 1 has a "floor" but Stage 2/3 don't need one?**
A: The 0.25% Stage 1 floor exists because 12-month ECL on a healthy, performing book can otherwise round down to a number regulators consider unrealistically low — the floor guards against under-provisioning on performing assets. Stage 2/3 already use lifetime ECL on deteriorating/impaired assets, which produces meaningfully larger numbers on its own without needing an artificial floor.

---

## I. RBI Regulatory Knowledge

**Q: What is the RBI's new ECL framework, and when does it take effect?**
A: The RBI (Commercial Banks — Asset Classification, Provisioning and Income Recognition) Directions, 2026, finalized April 2026, effective 1 April 2027 — replacing the older rules-based IRACP provisioning norms with a forward-looking Expected Credit Loss model. See `docs/regulatory_context.md` for full citations.

**Q: Describe the 3-stage classification under the new ECL Directions.**
A: Stage 1 (performing, no significant credit risk increase) → 12-month ECL with a 0.25% minimum floor. Stage 2 (Significant Increase in Credit Risk / SICR since origination, not yet impaired) → lifetime ECL. Stage 3 (credit-impaired, aligned with the existing 90-day NPA definition) → lifetime ECL. Implemented in this project's `06_regulatory_compliance/rbi_ecl_staging.R`.

**Q: How is the new ECL framework different from the old IRACP approach?**
A: IRACP was backward-looking and rules-based — provisioning triggered mechanically once an account crossed a fixed days-past-due threshold (e.g., 90 days = NPA). ECL is forward-looking and principles-based — banks must estimate expected future losses using PD/EAD/LGD models *before* an account actually turns delinquent, recognizing credit deterioration earlier.

**Q: What's the expected capital impact of the ECL shift, and why?**
A: Industry estimates suggest roughly a 120 basis point hit to banks' CET-1 capital ratios, phased over four years — because forward-looking, lifetime provisioning on Stage 2/3 assets is generally larger than the old rules-based provisions were, requiring banks to hold back more capital against expected losses earlier.

**Q: What triggers a Significant Increase in Credit Risk (SICR)?**
A: Conventionally (Basel/IFRS 9 practice, which RBI's framework follows) a rebuttable presumption of SICR at 30 days past due, alongside other qualitative/quantitative triggers like a significant relative increase in PD since origination, watchlist status, or restructuring. This project uses the 30-DPD trigger as its primary staging rule, explicitly flagged as a simplification given the absence of a real DPD ledger.

**Q: What are the RBI's Master Directions on Fraud Risk Management (2024), in brief?**
A: Revised and reissued 15 July 2024, consolidating 36 prior circulars, covering commercial banks/AIFIs, cooperative banks, and NBFCs separately. Key elements: governance requirements, Early Warning Signals and Red Flagging of Accounts for early detection, an 8-category fraud classification scheme, mandatory reporting timelines to RBI/law enforcement, and (new in 2024) natural justice requirements — notice, opportunity to represent, and a reasoned order — before classifying an account as fraud.

**Q: Why would natural justice requirements matter to a fraud risk analyst's day-to-day work?**
A: It changes the process, not just the detection — a flagged account can no longer be unilaterally classified as fraud; the customer must be notified and given a chance to respond before a final, reasoned classification. This means fraud workflows need a documented review/appeal step built in, not just a model score and an automatic action.

**Q: What does the RBI Credit Card and Debit Card Issuance and Conduct Directions require regarding account closure?**
A: As amended March 2024, card issuers face a penalty of ₹500 per *calendar* day (not just working days) for delays in closing a credit card account beyond the required timeline — a small but frequently-tested detail showing the direction's intent to remove issuer loopholes around business-day counting.

---

## J. Excel / Power BI / Reporting

**Q: Why use live formulas in an Excel report instead of pasting calculated values?**
A: Pasted values go stale the moment the underlying model reruns, and can't be audited by the recipient — a `=SUM(...)` formula lets a manager verify the total themselves and the workbook update automatically on refresh, which builds trust in the numbers.

**Q: What's the difference in audience/purpose between an Excel report and a Power BI dashboard?**
A: Excel serves an analyst or manager who wants to check, re-sort, and re-filter the underlying detail. Power BI serves a leadership audience who wants the headline number (KPI cards) in seconds, with drill-down available but not the default view — different tools for a "verify the work" audience versus a "brief me fast" audience.

**Q: What is DAX, and why does Power BI need its own calculation language instead of just SQL?**
A: DAX (Data Analysis Expressions) computes measures *within the context of the report's current filters/slicers* — e.g., a "Total Expected Loss" measure automatically recalculates for whatever stage/segment the user has clicked into, something a static SQL query can't do without being rerun. It's built for interactive, filter-aware calculation, not static querying.

**Q: How would you design a KPI card for a risk committee that needs to act fast?**
A: Semantic color coding (red/amber/green) tied to a defined threshold, not just a raw number — the audience should be able to tell "is this bad" in under a second, with the exact figure available on demand rather than as the primary visual signal.

**Q: What's a Population Stability Index chart, and would you show it on a dashboard?**
A: PSI tracks how much a scored population's distribution has shifted from a reference period — yes, worth a dashboard page for any deployed model, since it's the earliest warning sign a model needs retraining, well before its live AUC/KS visibly degrades.

**Q: How would you refresh a Power BI report connected to a changing model pipeline?**
A: Point the data connection at a stable, versioned output location (e.g., this project's `05_reporting/powerbi/extracts/` folder), rerun the upstream pipeline, then trigger Refresh in Power BI (manual or scheduled) — the report's visuals and DAX measures recalculate against the new data without rebuilding the report itself.

---

## K. Amex / Card Business Acumen

**Q: What are the main revenue levers for a card issuer?**
A: Interchange fees (paid by merchants on every swipe), interest income on revolving balances (customers who don't pay in full), and annual/membership fees — weighed against rewards program costs, funding costs, and credit losses.

**Q: Why might a "premium" card with a high annual fee and high rewards costs still be more profitable than a no-fee card?**
A: Premium cardholders typically have higher income, higher spend, and lower default rates — so even with richer rewards costs, the combination of higher interchange volume and lower credit losses can outweigh a mass-market no-fee card's thinner but "safer-looking" economics. This is the kind of "walk me through the unit economics" question Amex interviews specifically probe for.

**Q: How would you think about the trade-off between approving more applicants (growth) and keeping default rates low (risk)?**
A: Every risk cutoff is implicitly a growth-vs-loss trade-off — loosening approval criteria grows the book and revenue but raises expected loss; tightening protects loss rates but caps growth and cedes market share to competitors. A risk team's real job is finding the cutoff that maximizes *risk-adjusted* profit, not minimizing loss in isolation.

**Q: What's the difference between a closed-loop and open-loop card network, and why does it matter for a risk analyst at Amex specifically?**
A: Amex runs a closed-loop network (it's both the card issuer and the payment network, unlike Visa/Mastercard's open-loop model where banks issue cards on top of a separate network). This gives Amex direct visibility into both sides of a transaction (merchant and cardholder), which is a genuine data advantage for risk modeling that a typical bank issuer on an open-loop network doesn't have — worth mentioning if asked what's distinctive about Amex's risk function.

**Q: How would you approach setting a new customer's initial credit limit?**
A: Based on application-scoring PD, income/debt-to-income signals, bureau data, and portfolio-level guardrails (e.g., max exposure per risk tier) — balancing the expected-loss cost of a limit that's too high against the lost-revenue cost of a limit too conservative for a genuinely low-risk customer.

**Q: What macro factors would you watch as a portfolio risk analyst?**
A: Unemployment rate (directly drives default risk), inflation (squeezes disposable income, raises revolving balances), interest rates (affects both funding costs and customers' ability to service debt), and consumer confidence indices as a leading indicator of spend and repayment behavior shifts.

**Q: How would delinquency differ between a recession and a normal economic period, and how should a risk model account for that?**
A: Delinquency and default rates rise across the board in a recession, often faster than pure PD models trained on normal-period data would predict — which is exactly why stress testing with macro-scenario PD multipliers (see the Portfolio Risk section) exists as a separate layer on top of the baseline model, rather than trusting the baseline model alone through a downturn.

**Q: How would you communicate a rising delinquency trend to a non-risk stakeholder (e.g., a product manager)?**
A: Lead with the business impact, not the statistic — "if this trend continues, we're on track for $X in additional losses next quarter, concentrated in [segment]" — then the supporting numbers, not the reverse. Product managers respond to decisions and dollar impact, not KS statistics.

---

## L. Behavioral / Case Study / Communication

**Q: Walk me through a project on your resume.**
A: Narrate it as a pipeline, in order: raw data → cleaning/feature engineering → modeling → business translation (expected loss/reporting) — this shows you think in systems, not isolated techniques. Use this project's own stage structure as the narration scaffold.

**Q: Tell me about a time you had to explain a technical result to a non-technical audience.**
A: Structure: situation (what was being asked), the technical finding, the *translation* you made (e.g., "AUC of 0.70" became "our model correctly ranks a risky customer above a safe one about 7 times out of 10"), and the outcome/decision that followed. Interviewers are testing the translation step specifically, not the technical accuracy.

**Q: Describe a time you disagreed with a modeling or business decision.**
A: Use a structure that shows you raised the concern with data/reasoning (not just an opinion), stayed collaborative rather than combative, and describe the actual resolution honestly — including if the decision went the other way and how you executed on it anyway.

**Q: How do you stay current with regulatory changes (e.g., RBI directions)?**
A: Name concrete sources/habits — regulator circulars and master directions directly, industry commentary (law firm/Big 4 analyses like the ones cited in `docs/regulatory_context.md`), and translating each significant change into "what does this mean for a model/process I actually own" rather than passively reading updates.

**Q: How would you prioritize your work if given three competing risk requests in one week?**
A: Frame it around dollar/risk impact and deadline hardness, not just "whoever asked first" — e.g., a regulatory reporting deadline is generally non-negotiable, a stakeholder's "nice to have" analysis can flex, and anything tied to an active/growing loss trend gets escalated regardless of who asked.

**Q: What's a mistake you made in an analysis, and what did you learn?**
A: Be specific and genuine rather than a disguised humble-brag — describe the actual error (e.g., a metric chosen that hid a class-imbalance problem), how it was caught, and the concrete process change you made afterward (e.g., "I now always check base rate before picking a metric").

**Q: Why risk management specifically, and why at a company like Amex?**
A: Tie your answer to something specific and checkable — e.g., the closed-loop network's data advantage, the scale of the portfolio, or the specific blend of quantitative modeling and real business consequence risk roles offer compared to pure research roles — avoid generic "I like data and helping people" answers.

**Q: How do you handle being wrong when a model you built underperforms after deployment?**
A: Emphasize monitoring discipline (you'd have caught it via population stability/calibration tracking, not just hoped), a clear diagnosis process (data drift vs. genuine model flaw vs. changed macro conditions), and treating it as expected model lifecycle behavior to manage, not a personal failure to hide.
