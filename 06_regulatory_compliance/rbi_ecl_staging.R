# ============================================================
# RBI ECL (Expected Credit Loss) staging & disclosure report.
#
# Implements the 3-stage classification and provisioning logic
# introduced by the RBI (Commercial Banks -- Asset Classification,
# Provisioning and Income Recognition) Directions, 2026 -- the new
# ECL framework that replaces the old IRACP provisioning norms,
# effective 1 April 2027. [Source: RBI notification, April 2026;
# see docs/regulatory_context.md for citations.]
#
# This reframes the PD x EAD x LGD expected-loss logic already in
# 04_portfolio_risk/expected_loss.R into the *exact* stage structure
# and disclosure table RBI's directions actually require, instead of
# a generic book-level expected-loss number.
#
# Stage rules (per the Directions):
#   Stage 1 -- performing, no Significant Increase in Credit Risk (SICR)
#              -> 12-month ECL, subject to a 0.25% minimum floor
#   Stage 2 -- SICR since origination, not yet credit-impaired
#              -> lifetime ECL
#   Stage 3 -- credit-impaired (aligns with RBI's existing 90-day NPA
#              definition) -> lifetime ECL
#
# [ASSUMPTION] This project has no real days-past-due (DPD) ledger, so
# DPD is proxied from the delinquency_score feature already in the
# credit model output. In a real deployment this would be sourced
# directly from the loan management system, not derived from a model
# feature. The 30-DPD SICR trigger and 90-DPD default trigger below
# are the standard Basel/IFRS 9 conventions RBI's own NPA definition
# already uses -- not invented for this project.
#
# [ASSUMPTION] "Lifetime" for an undrawn/revolving card facility is
# approximated here as a fixed 3-year behavioral life, a common
# simplification for revolving products under IFRS 9-style ECL models.
# A production model would derive this from actual account attrition/
# utilization behavior.
#
# Run:
#   Rscript rbi_ecl_staging.R
# ============================================================

library(dplyr)
library(readr)

this_file <- sub("--file=", "", grep("--file=", commandArgs(trailingOnly = FALSE), value = TRUE))
script_dir <- if (length(this_file) > 0) dirname(normalizePath(this_file)) else getwd()
root <- dirname(script_dir)
out_dir <- file.path(script_dir, "output")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

# --- 1. Load scored customers (PD + balance) from the credit model ------
scored_path <- file.path(root, "02_credit_risk", "python", "output", "scored_customers.csv")

if (file.exists(scored_path)) {
  book <- read_csv(scored_path, show_col_types = FALSE) |>
    rename(pd_12m = predicted_pd, ead = balance) |>
    select(customer_id, ead, pd_12m, delinquency_score)
} else {
  message("No scored_customers.csv found -- run 02_credit_risk/python/train_credit_model.py first.")
  message("Falling back to synthetic data for a runnable demo.")
  set.seed(42)
  n <- 20000
  book <- tibble(
    customer_id = sprintf("CUST_%07d", 1:n),
    ead = pmax(rgamma(n, shape = 2, scale = 1500), 0),
    pd_12m = pmin(pmax(rbeta(n, 2, 12), 0.001), 0.95),
    delinquency_score = pmin(pmax(rbeta(n, 1.5, 6), 0), 1)
  )
}

# --- 2. Proxy days-past-due from delinquency_score (see caveat above) ---
book <- book |>
  mutate(dpd_proxy = round(pmin(delinquency_score * 150, 180)))

# --- 3. Stage classification -----------------------------------------
LIFETIME_YEARS <- 3          # [ASSUMPTION] revolving-card behavioral life
STAGE1_FLOOR_PCT <- 0.0025   # RBI-mandated 0.25% minimum floor, Stage 1

book <- book |>
  mutate(
    stage = case_when(
      dpd_proxy >= 90 ~ "Stage 3 (Credit-Impaired / NPA)",
      dpd_proxy >= 30 ~ "Stage 2 (SICR)",
      TRUE ~ "Stage 1 (Performing)"
    ),
    lgd = if_else(pd_12m > 0.5, 0.75, 0.65),
    # lifetime PD via simple cumulative-default approximation:
    # 1 - probability of surviving every year of the horizon without default
    lifetime_pd = 1 - (1 - pd_12m) ^ LIFETIME_YEARS,
    ecl_unfloored = if_else(
      stage == "Stage 1 (Performing)",
      pd_12m * ead * lgd,          # 12-month ECL
      lifetime_pd * ead * lgd      # lifetime ECL, Stage 2 & 3
    ),
    ecl = if_else(
      stage == "Stage 1 (Performing)",
      pmax(ecl_unfloored, STAGE1_FLOOR_PCT * ead),  # apply the 0.25% floor
      ecl_unfloored
    )
  )

write_csv(
  book |> select(customer_id, ead, pd_12m, dpd_proxy, stage, lgd, lifetime_pd, ecl),
  file.path(out_dir, "rbi_ecl_staged_accounts.csv")
)

# --- 4. Credit quality disclosure table --------------------------------
# This is the exact table shape RBI's directions require: gross carrying
# amount, ECL provision, and net carrying amount, broken out by stage.
disclosure <- book |>
  group_by(stage) |>
  summarise(
    n_accounts = n(),
    gross_carrying_amount = sum(ead),
    ecl_provision = sum(ecl),
    net_carrying_amount = gross_carrying_amount - ecl_provision,
    coverage_ratio_pct = round(100 * ecl_provision / gross_carrying_amount, 3),
    .groups = "drop"
  ) |>
  arrange(match(stage, c("Stage 1 (Performing)", "Stage 2 (SICR)", "Stage 3 (Credit-Impaired / NPA)")))

totals <- disclosure |>
  summarise(
    stage = "Total",
    n_accounts = sum(n_accounts),
    gross_carrying_amount = sum(gross_carrying_amount),
    ecl_provision = sum(ecl_provision),
    net_carrying_amount = sum(net_carrying_amount),
    coverage_ratio_pct = round(100 * sum(ecl_provision) / sum(gross_carrying_amount), 3)
  )

disclosure_with_total <- bind_rows(disclosure, totals)
print(disclosure_with_total)
write_csv(disclosure_with_total, file.path(out_dir, "rbi_credit_quality_disclosure.csv"))

cat(sprintf("\nWrote rbi_ecl_staged_accounts.csv and rbi_credit_quality_disclosure.csv to %s\n", out_dir))
cat("This disclosure table format mirrors what RBI's Commercial Banks Asset\n")
cat("Classification, Provisioning and Income Recognition Directions, 2026\n")
cat("require banks to report per stage, per reporting period. See\n")
cat("docs/regulatory_context.md for the full citation trail and assumptions.\n")
