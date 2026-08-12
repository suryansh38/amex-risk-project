# ============================================================
# Credit risk: traditional logistic-regression scorecard.
#
# This is the interview-standard technique risk teams use
# alongside (not instead of) ML models like the XGBoost one in
# ../python/train_credit_model.py -- scorecards are preferred
# for adjudication decisions because they're monotonic,
# interpretable, and easy to justify to regulators/customers
# (Reg B adverse-action reasons).
#
# Pipeline: WOE binning -> Information Value screening ->
#           logistic regression -> points-based scorecard.
#
# Run:
#   Rscript scorecard_model.R
# Requires: install.packages(c("scorecard", "dplyr", "readr"))
# ============================================================

library(scorecard)
library(dplyr)
library(readr)

# Resolve paths relative to this script's own location, so it can be run
# from any working directory: Rscript 02_credit_risk/r/scorecard_model.R
this_file <- sub("--file=", "", grep("--file=", commandArgs(trailingOnly = FALSE), value = TRUE))
script_dir <- if (length(this_file) > 0) dirname(normalizePath(this_file)) else getwd()
root <- dirname(dirname(script_dir))  # 02_credit_risk/r -> 02_credit_risk -> repo root

processed_dir <- file.path(root, "data", "processed", "credit_risk_features")
raw_dir <- file.path(root, "data", "raw", "credit_risk")
out_dir <- file.path(script_dir, "output")

load_features <- function() {
  parquet_files <- list.files(processed_dir, pattern = "\\.parquet$", recursive = TRUE, full.names = TRUE)
  if (length(parquet_files) > 0 && requireNamespace("arrow", quietly = TRUE)) {
    return(arrow::open_dataset(processed_dir) |> dplyr::collect())
  }

  synthetic_path <- file.path(raw_dir, "synthetic_train.csv")
  if (!file.exists(synthetic_path)) {
    stop("No processed data and no synthetic CSV found. Run: python ../../01_data_engineering/synthetic_data.py")
  }
  df <- read_csv(synthetic_path, show_col_types = FALSE)
  df |> rename(
    customer_id       = customer_ID,
    balance           = B_1_balance,
    spend             = S_1_spend,
    payment_ratio     = P_1_payment_ratio,
    delinquency_score = D_1_delinquency_score,
    utilization       = B_2_utilization,
    risk_score        = R_1_risk_score,
    tenure_months     = D_2_tenure_months
  )
}

df <- load_features() |>
  select(balance, spend, payment_ratio, delinquency_score,
         utilization, risk_score, tenure_months, target) |>
  na.omit()

# --- 1. Train/test split -----------------------------------------------
split <- split_df(df, y = "target", ratio = 0.75, seed = 42)
train <- split$train
test  <- split$test

# --- 2. WOE binning + Information Value screening -----------------------
# IV < 0.02 = useless, 0.02-0.1 = weak, 0.1-0.3 = medium, 0.3+ = strong
bins <- woebin(train, y = "target")
iv_summary <- lapply(names(bins), function(v) {
  data.frame(variable = v, iv = round(unique(bins[[v]]$total_iv), 4))
}) |> bind_rows() |> arrange(desc(iv))

cat("Information Value by feature (screen anything below ~0.02):\n")
print(iv_summary)

keep_vars <- iv_summary$variable[iv_summary$iv >= 0.02]

# --- 3. Apply WOE transform, fit logistic regression ---------------------
train_woe <- woebin_ply(train[, c(keep_vars, "target")], bins[keep_vars])
test_woe  <- woebin_ply(test[, c(keep_vars, "target")], bins[keep_vars])

model <- glm(target ~ ., family = binomial(), data = train_woe)
cat("\nLogistic regression summary:\n")
print(summary(model))

# --- 4. Convert to a points-based scorecard ------------------------------
# base 660 / 40 pts-to-double-odds is a standard card-issuer convention
card <- scorecard(bins, model, points0 = 660, odds0 = 1 / 19, pdo = 40)

train_score <- scorecard_ply(train, card)
test_score  <- scorecard_ply(test, card)

# --- 5. Evaluate: AUC, KS, Gini (same metrics as the Python model, for
#         a like-for-like comparison between the two approaches) --------
pred_test <- predict(model, newdata = test_woe, type = "response")
perf <- perf_eva(pred_test, test$target, show_plot = FALSE)

cat(sprintf("\nScorecard AUC: %.4f | KS: %.4f | Gini: %.4f\n",
            perf$binomial_metric$dat$AUC,
            perf$binomial_metric$dat$KS,
            perf$binomial_metric$dat$Gini))

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
write_csv(iv_summary, file.path(out_dir, "information_value.csv"))
write_csv(cbind(test, score = test_score$score, predicted_pd = pred_test),
          file.path(out_dir, "scorecard_scored_customers.csv"))

cat(sprintf("\nWrote information_value.csv and scorecard_scored_customers.csv to %s\n", out_dir))
