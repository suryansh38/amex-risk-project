# ============================================================
# Portfolio risk: expected loss, vintage analysis, stress testing.
#
# Consumes the PD scores produced by 02_credit_risk/python/train_credit_model.py
# (falls back to synthetic data if that hasn't been run) and rolls
# customer-level PD up to book-level risk metrics -- the layer a
# portfolio risk / risk strategy analyst actually owns, distinct from
# the model-building layer.
#
# EL = PD x EAD x LGD  (the standard expected-loss identity)
#   PD  = probability of default (from the credit risk model)
#   EAD = exposure at default (approximated here as current balance)
#   LGD = loss given default (card industry convention: ~65-75% for
#         unsecured revolving credit, since recovery is low without collateral)
#
# Run:
#   Rscript expected_loss.R
# ============================================================

library(dplyr)
library(readr)
library(ggplot2)

this_file <- sub("--file=", "", grep("--file=", commandArgs(trailingOnly = FALSE), value = TRUE))
script_dir <- if (length(this_file) > 0) dirname(normalizePath(this_file)) else getwd()
root <- dirname(script_dir)  # 04_portfolio_risk -> repo root
out_dir <- file.path(script_dir, "output")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# --- 1. Load scored customers (PD) --------------------------------------
scored_path <- file.path(root, "02_credit_risk", "python", "output", "scored_customers.csv")

if (file.exists(scored_path)) {
  book <- read_csv(scored_path, show_col_types = FALSE) |>
    rename(pd = predicted_pd)
} else {
  message("No scored_customers.csv found -- run 02_credit_risk/python/train_credit_model.py first.")
  message("Falling back to synthetic PDs for a runnable demo.")
  set.seed(42)
  n <- 20000
  book <- tibble(
    customer_id = sprintf("CUST_%07d", 1:n),
    balance = pmax(rgamma(n, shape = 2, scale = 1500), 0),
    pd = pmin(pmax(rbeta(n, 2, 12), 0.001), 0.95)
  )
}

# --- 2. Assign exposure (EAD) and loss-given-default (LGD) ---------------
# LGD varies by risk tier in reality (secured vs. unsecured, vintage,
# collections effectiveness) -- modeled here as a fixed unsecured-card
# assumption with a small stress add-on for the highest-PD segment.
book <- book |>
  mutate(
    ead = balance,
    lgd = if_else(pd > 0.5, 0.75, 0.65),
    expected_loss = pd * ead * lgd
  )

# --- 3. Book-level expected loss summary ----------------------------------
summary_stats <- book |>
  summarise(
    n_accounts = n(),
    total_exposure = sum(ead),
    total_expected_loss = sum(expected_loss),
    el_rate_pct = round(100 * sum(expected_loss) / sum(ead), 3),
    avg_pd_pct = round(100 * mean(pd), 3)
  )
print(summary_stats)
write_csv(summary_stats, file.path(out_dir, "book_summary.csv"))

# --- 4. Risk-tier / decile breakdown (what actually goes in a risk deck) --
tier_summary <- book |>
  mutate(pd_decile = ntile(pd, 10)) |>
  group_by(pd_decile) |>
  summarise(
    n_accounts = n(),
    exposure = sum(ead),
    expected_loss = sum(expected_loss),
    avg_pd_pct = round(100 * mean(pd), 3),
    .groups = "drop"
  )
write_csv(tier_summary, file.path(out_dir, "expected_loss_by_decile.csv"))

# --- 5. Stress testing ------------------------------------------------------
# Apply macro shock multipliers to PD -- mirrors CCAR/DFAST-style
# severely-adverse scenario design (unemployment shock -> PD multiplier)
stress_scenarios <- tibble(
  scenario = c("Baseline", "Moderate Recession", "Severe Recession (CCAR-style)"),
  pd_multiplier = c(1.0, 1.5, 2.3)
)

stress_results <- stress_scenarios |>
  rowwise() |>
  mutate(
    stressed_el = sum(pmin(book$pd * pd_multiplier, 1.0) * book$ead * book$lgd)
  ) |>
  ungroup() |>
  mutate(el_rate_pct = round(100 * stressed_el / sum(book$ead), 3))

print(stress_results)
write_csv(stress_results, file.path(out_dir, "stress_test_results.csv"))

# --- 6. Vintage-style loss curve (synthetic month-on-book decay pattern) --
# Real vintage analysis needs origination-date cohorts; approximated here
# via a canonical credit-card loss curve shape (ramps, peaks ~month 12-18,
# decays) applied to the book's total expected loss, for the dashboard demo.
months_on_book <- 1:36
loss_curve_shape <- dgamma(months_on_book, shape = 3, rate = 0.25)
loss_curve_shape <- loss_curve_shape / sum(loss_curve_shape)
vintage_curve <- tibble(
  month_on_book = months_on_book,
  cumulative_loss_pct = round(100 * cumsum(loss_curve_shape), 3)
)
write_csv(vintage_curve, file.path(out_dir, "vintage_loss_curve.csv"))

# --- 7. Save a chart for quick visual sanity-check (feeds reporting deck) -
p <- ggplot(tier_summary, aes(x = pd_decile, y = expected_loss / 1e6)) +
  geom_col(fill = "#1A365D") +
  labs(title = "Expected Loss by PD Decile", x = "PD Decile (1=lowest risk)",
       y = "Expected Loss ($M)") +
  theme_minimal()
ggsave(file.path(out_dir, "expected_loss_by_decile.png"), p, width = 7, height = 4.5)

cat(sprintf("\nWrote book_summary.csv, expected_loss_by_decile.csv, stress_test_results.csv,\n"))
cat(sprintf("vintage_loss_curve.csv, expected_loss_by_decile.png to %s\n", out_dir))
cat("-> feeds 05_reporting/ (Excel workbook + Power BI extracts)\n")
