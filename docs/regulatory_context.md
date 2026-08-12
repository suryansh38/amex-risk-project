# Regulatory Context — RBI Master Directions

Why this module exists: an Amex-facing (or any India-based card issuer/NBFC)
risk role expects fluency in the *actual current* regulatory framework, not
just modeling technique. This project maps directly onto three live RBI
frameworks. All facts below are sourced (linked) — treat anything not
explicitly cited, or marked `[ASSUMPTION]`, as a project-level simplification
made because this is synthetic data, not RBI guidance itself.

## 1. The new ECL framework (`06_regulatory_compliance/`)

**RBI (Commercial Banks — Asset Classification, Provisioning and Income
Recognition) Directions, 2026** — finalized April 2026, effective **1 April
2027**. Replaces the old IRACP (Income Recognition, Asset Classification,
Provisioning) rules-based norms with a forward-looking **Expected Credit
Loss (ECL)** framework, requiring banks to estimate credit losses at every
reporting date using PD, EAD, and LGD — described as India's biggest
banking-regulation shift since the 1990s.

- 3-stage classification:
  - **Stage 1** (performing) → 12-month ECL, 0.25% minimum floor
  - **Stage 2** (Significant Increase in Credit Risk / SICR, not yet
    impaired) → lifetime ECL
  - **Stage 3** (credit-impaired, aligned with RBI's existing 90-day NPA
    definition) → lifetime ECL
- Applies to commercial banks (excluding small finance banks, payments
  banks, local area banks) and SBI.
- Estimated to reduce banks' CET-1 capital ratio by ~120 basis points,
  phased over four years.

Sources:
- [TaxGuru — Complete Analysis of ECL Framework for Commercial Banks under RBI Directions, 2026](https://taxguru.in/rbi/complete-analysis-ecl-framework-commercial-banks-rbi-directions-2026.html)
- [Regnology — Reserve Bank of India's Expected Credit Loss (ECL) Directions](https://www.regnology.net/en/resources/regulatory-topics/reserve-bank-of-indias-ecl-directions/)
- [Mondaq — RBI Notifies Commercial Banks Asset Classification, Provisioning and Income Recognition Directions, 2026](https://www.mondaq.com/india/financial-services/1785568/rbi-notifies-reserve-bank-of-india-commercial-banks-asset-classification-provisioning-and-income-recognition-directions-2026)

**What `06_regulatory_compliance/rbi_ecl_staging.R` does**: takes the PD
scores from `02_credit_risk/python/train_credit_model.py` and restages the
book into these exact 3 stages, computing 12-month ECL (Stage 1, with the
0.25% floor applied) vs. lifetime ECL (Stage 2/3), then produces the
credit-quality disclosure table (gross carrying amount / ECL / net carrying
amount / coverage ratio, by stage) in the shape the Directions require.

`[ASSUMPTION]` this project has no real days-past-due ledger, so DPD is
proxied from the `delinquency_score` model feature — see the script's
header comment for the full list of simplifications. The 30-DPD (SICR) and
90-DPD (default) thresholds themselves are *not* invented — they're the
standard Basel/IFRS 9 convention that RBI's own existing NPA definition
already uses.

## 2. Fraud Risk Management (`03_fraud_risk/`)

**RBI Master Directions on Fraud Risk Management** — revised and reissued
15 July 2024, effective the same date, superseding and consolidating 36
prior circulars. Three near-identical directions cover (i) commercial banks
and All-India Financial Institutions, (ii) cooperative banks, (iii) NBFCs
including Housing Finance Companies.

Key requirements: governance for fraud risk management, **Early Warning
Signals (EWS)** and **Red Flagging of Accounts (RFA)** for early detection,
fraud classification across **8 prescribed categories**, mandatory
reporting timelines to RBI and law enforcement, staff accountability, and
(a significant 2024 change) **natural justice** requirements — notice,
opportunity to represent, and a reasoned order — before an account can be
classified as fraud.

Source: [TaxGuru — RBI Master Directions on Fraud Risk Management in Banks & Financial Institutions](https://taxguru.in/rbi/rbi-master-directions-fraud-risk-management-banks-financial-institutions.html)

This project's `03_fraud_risk/train_fraud_model.py` builds the *detection*
layer these directions assume already exists (an EWS-style scoring model).
It does not yet implement the 8-category classification or reporting
workflow — worth naming explicitly as a gap/extension opportunity in an
interview rather than overclaiming coverage.

## 3. Credit Card Issuance & Conduct (context for `02_credit_risk/`)

**Master Direction — Reserve Bank of India (Credit Card and Debit Card —
Issuance and Conduct) Directions, 2022**, issued 21 April 2022, effective
1 July 2022, with amendments in March 2024 (business-card end-use
monitoring, ₹500/day penalty for delayed account closure regardless of
working days, wearable form factors permitted).

Source: [KS&K — Updates to RBI Master Direction on Credit and Debit Card Issuance and Conduct](https://ksandk.com/newsletter/rbi-master-direction-on-credit-debit-cards-updates/)

This is the conduct/consumer-protection layer sitting alongside the credit
*risk* modeling this project does — relevant context for interview
questions about customer-facing obligations, not something the project
implements directly.

## How to talk about this in an interview

- Lead with the ECL framework — it's the most current, most technically
  substantial, and most likely to come up given its April 2027 effective
  date is imminent for the industry.
- Be precise about what's real regulation vs. project simplification: the
  stage definitions and thresholds are RBI's actual rules; the DPD proxy
  and 3-year lifetime assumption are stated, sourced simplifications made
  because this project runs on synthetic data.
- If asked "why does this matter for a card issuer, not just a bank" —
  Amex India operates as a banking/NBFC-regulated entity for its card
  business, so the same ECL shift applies to how it must provision for
  card receivables going forward.
