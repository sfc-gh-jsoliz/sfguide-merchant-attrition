-- ============================================================================
-- Merchant Attrition Early-Warning — setup.sql  (DEPLOY mode: real category data)
-- ----------------------------------------------------------------------------
-- Merchant Attrition Early-Warning for a payments processor / acquirer.
-- Flags merchants whose processed volume is decaying toward churn, and
-- contextualizes that decline against REAL US Census Advance Retail Sales by
-- category (the category demand backdrop) from the free Snowflake Marketplace
-- "Financial Data Package" (SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE).
--
-- A specific acquirer's merchant-level volume has no public source, so
-- ATTRITION_MERCHANT / ATTRITION_MERCHANT_MONTHLY are synthetic in both modes;
-- here the CATEGORY backdrop is REAL. To use your own book, replace those two
-- tables with your settlement + engagement data (same columns) via Cortex Code.
--
-- Prereq: mount the free "Financial Data Package" listing from the Marketplace.
-- Run setup_synthetic.sql instead for a no-listing TRY.
--
-- Fixed seeds via HASH(merchant_id || key) → re-runs are stable.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS SNOWPACK_MERCHANT_ATTRITION;
CREATE SCHEMA IF NOT EXISTS SNOWPACK_MERCHANT_ATTRITION.CORE;
CREATE WAREHOUSE IF NOT EXISTS SNOWPACK_MERCHANT_ATTRITION_WH
  WITH WAREHOUSE_SIZE='XSMALL' AUTO_SUSPEND=60 AUTO_RESUME=TRUE INITIALLY_SUSPENDED=TRUE;
USE WAREHOUSE SNOWPACK_MERCHANT_ATTRITION_WH;
USE SCHEMA SNOWPACK_MERCHANT_ATTRITION.CORE;

-- Type-switch drops: ATTRITION_CATEGORY_HEALTH is a VIEW here / TABLE in
-- setup_synthetic.sql. Drop dependents first, then both type variants, so
-- switching modes in the shared schema never hits a VIEW/TABLE type conflict.
DROP SEMANTIC VIEW IF EXISTS ATTRITION_SV;
DROP VIEW IF EXISTS ATTRITION_BENCHMARK;
DROP VIEW IF EXISTS ATTRITION_CATEGORY_HEALTH;
DROP TABLE IF EXISTS ATTRITION_CATEGORY_HEALTH;

-- 1. Category dimension: MCC-aligned categories mapped to Census codes --------
CREATE OR REPLACE TABLE ATTRITION_MERCHANT_CATEGORY (
  category_code STRING, category_name STRING, mcc STRING, census_variable STRING
);
INSERT INTO ATTRITION_MERCHANT_CATEGORY VALUES
  ('RESTAURANTS','Restaurants & Food Service','5812','ADV_722SM_SA'),
  ('APPAREL','Clothing & Accessories','5651','ADV_448SM_SA'),
  ('ELECTRONICS','Electronics & Appliances','5732','ADV_443SM_SA'),
  ('GROCERY','Food & Beverage Stores','5411','ADV_445SM_SA'),
  ('FURNITURE','Furniture & Home Furnishings','5712','ADV_442SM_SA'),
  ('HEALTH','Health & Personal Care','5912','ADV_446SM_SA');

-- 24 months ending 2026-06-30 (month-end dates to align with Census vintages)
CREATE OR REPLACE TEMP TABLE ATTRITION_months AS
SELECT LAST_DAY(DATEADD(month, SEQ4(), '2024-07-01')) AS month_end, SEQ4() AS m_idx
FROM TABLE(GENERATOR(ROWCOUNT => 24));

-- Per-category scale for baseline merchant volume (relative size of the vertical)
CREATE OR REPLACE TEMP TABLE ATTRITION_catscale (category_code STRING, scale FLOAT) AS
SELECT * FROM VALUES
  ('RESTAURANTS', 1.30),
  ('APPAREL',     0.80),
  ('ELECTRONICS', 0.90),
  ('GROCERY',     1.20),
  ('FURNITURE',   0.70),
  ('HEALTH',      1.00)
  AS s(category_code, scale);

-- 2. Merchant master (synthetic; swap for your merchant data) -----------------
-- 20 merchants per category = 120 merchants. All per-merchant attributes are
-- deterministic functions of merchant_id via HASH() so re-runs are identical.
--   is_churner      ~30% of merchants decay toward churn
--   decay_start_idx month index (6..21) when decay begins for a churner
--   decay_len       3..8 months from first decline to churned
CREATE OR REPLACE TABLE ATTRITION_MERCHANT
  COMMENT = 'SYNTHETIC: merchant master for a payments processor (MID, MCC, category, onboarding, baseline volume).'
AS
WITH seqs AS (
  SELECT SEQ4() + 1 AS merchant_num FROM TABLE(GENERATOR(ROWCOUNT => 20))
),
base AS (
  SELECT
    c.category_code,
    c.category_name,
    c.mcc,
    c.category_code || '-' || LPAD(s.merchant_num::string, 3, '0') AS merchant_id,
    s.merchant_num
  FROM ATTRITION_MERCHANT_CATEGORY c CROSS JOIN seqs s
)
SELECT
  b.merchant_id,
  'Merchant ' || b.merchant_id AS merchant_name,
  b.mcc,
  b.category_code,
  b.category_name,
  DATEADD(month, -(MOD(ABS(HASH(b.merchant_id || 'onb')), 48)), DATE '2024-07-01') AS onboarded_date,
  ROUND((MOD(ABS(HASH(b.merchant_id || 'vol')), 480001) + 20000) * cs.scale, 0) AS baseline_monthly_volume,
  (MOD(ABS(HASH(b.merchant_id || 'chn')), 100) < 30)                AS is_churner,
  6 + MOD(ABS(HASH(b.merchant_id || 'dsi')), 16)                    AS decay_start_idx,
  3 + MOD(ABS(HASH(b.merchant_id || 'dl')), 6)                      AS decay_len
FROM base b JOIN ATTRITION_catscale cs USING (category_code);

-- 3. Monthly volume / health fact (synthetic; swap for your settlements) -------
-- Healthy merchants grow slowly with small noise; churners decay linearly to
-- ~0 over decay_len months starting at decay_start_idx, then stay churned.
CREATE OR REPLACE TABLE ATTRITION_MERCHANT_MONTHLY
  COMMENT = 'SYNTHETIC: monthly processed volume and health signals per merchant. Replace with your settlement + engagement data (same columns) to go live.'
AS
WITH mm AS (
  SELECT
    m.merchant_id, m.category_code, m.category_name, m.baseline_monthly_volume,
    m.is_churner, m.decay_start_idx, m.decay_len,
    (m.decay_start_idx + m.decay_len) AS churn_complete_idx,
    mo.month_end, mo.m_idx,
    ((MOD(ABS(HASH(m.merchant_id || mo.m_idx || 'noise')), 11) - 5) / 100.0) AS noise
  FROM ATTRITION_MERCHANT m CROSS JOIN ATTRITION_months mo
),
calc AS (
  SELECT
    merchant_id, category_code, category_name, month_end, m_idx,
    baseline_monthly_volume, is_churner, decay_start_idx, decay_len, churn_complete_idx,
    CASE
      WHEN NOT is_churner                 THEN 1.0
      WHEN m_idx < decay_start_idx        THEN 1.0
      WHEN m_idx >= churn_complete_idx    THEN 0.02
      ELSE 1.0 - ((m_idx - decay_start_idx)::float / NULLIF(decay_len, 0)) * 0.95
    END AS decay_factor,
    (is_churner AND m_idx >= churn_complete_idx) AS churned_flag,
    noise
  FROM mm
)
SELECT
  merchant_id,
  month_end,
  GREATEST(ROUND(baseline_monthly_volume * (1 + 0.004 * m_idx) * decay_factor * (1 + noise), 0), 0) AS monthly_volume_usd,
  GREATEST(ROUND(baseline_monthly_volume * (1 + 0.004 * m_idx) * decay_factor * (1 + noise) / 85.0, 0), 0) AS txn_count,
  CASE
    WHEN churned_flag              THEN 60 + (m_idx - churn_complete_idx) * 30
    WHEN decay_factor < 1.0        THEN ROUND(5 + (1 - decay_factor) * 50, 0)
    ELSE MOD(ABS(HASH(merchant_id || m_idx || 'dslt')), 11)
  END AS days_since_last_txn,
  CASE
    WHEN churned_flag              THEN 0
    WHEN decay_factor < 1.0        THEN ROUND(2 + (1 - decay_factor) * 4, 0)
    ELSE MOD(ABS(HASH(merchant_id || m_idx || 'tix')), 2)
  END AS support_tickets,
  churned_flag
FROM calc;

-- 4. Category backdrop — REAL US Census Advance Retail Sales (deduped vintage) -
-- Latest-vintage monthly category sales with MoM / YoY growth. Pulls a 36-month
-- window so YoY has a prior-year anchor; the benchmark only joins the 24-month
-- synthetic window.
CREATE OR REPLACE VIEW ATTRITION_CATEGORY_HEALTH
  COMMENT = 'REAL category market sales + growth, from SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE (US Census Advance Retail Sales, seasonally adjusted, USD).'
AS
WITH ts AS (
  SELECT variable, date,
         ROW_NUMBER() OVER (PARTITION BY variable, date ORDER BY _EFFECTIVE_START_TIMESTAMP DESC) AS rn,
         value
  FROM SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE.COMMERCIAL_BANKING.FINANCIAL_ECONOMIC_INDICATORS_TIMESERIES_PIT
  WHERE variable IN (SELECT census_variable FROM ATTRITION_MERCHANT_CATEGORY)
    AND date >= DATE '2023-07-01'
),
raw AS (
  SELECT c.category_code, c.category_name,
         LAST_DAY(ts.date) AS month_end,
         ts.value AS market_sales_usd
  FROM ts
  JOIN ATTRITION_MERCHANT_CATEGORY c ON c.census_variable = ts.variable
  WHERE ts.rn = 1
)
SELECT
  category_code, category_name, month_end, market_sales_usd,
  ROUND((market_sales_usd / NULLIF(LAG(market_sales_usd, 1)  OVER (PARTITION BY category_code ORDER BY month_end), 0) - 1) * 100, 2) AS mom_growth_pct,
  ROUND((market_sales_usd / NULLIF(LAG(market_sales_usd, 12) OVER (PARTITION BY category_code ORDER BY month_end), 0) - 1) * 100, 2) AS yoy_growth_pct
FROM raw;

-- 5. Wide benchmark view (single pre-joined grain for the semantic view) -------
-- Grain = (category_code, month_end, risk_band, tenure_band): the synthetic
-- merchant fact is pre-aggregated to this grain BEFORE joining the category
-- backdrop, so fact metrics never fan out. The REAL category backdrop is at
-- (category_code, month_end) and repeats across risk/tenure buckets, so it is
-- exposed ONLY as AVG/MAX (non-additive) metrics in the semantic view.
CREATE OR REPLACE VIEW ATTRITION_BENCHMARK
  COMMENT = 'Merchant attrition health by category/month/risk_band/tenure_band vs REAL category demand backdrop.'
AS
WITH per_merchant AS (
  SELECT
    mm.merchant_id, mm.month_end,
    mer.category_code, mer.category_name, mer.baseline_monthly_volume, mer.onboarded_date,
    mm.monthly_volume_usd, mm.txn_count, mm.days_since_last_txn, mm.support_tickets, mm.churned_flag,
    (mm.monthly_volume_usd / NULLIF(mer.baseline_monthly_volume, 0)) AS vol_ratio,
    ROUND((mer.baseline_monthly_volume - mm.monthly_volume_usd) / NULLIF(mer.baseline_monthly_volume, 0) * 100, 2) AS volume_decline_pct,
    DATEDIFF(month, mer.onboarded_date, mm.month_end) AS tenure_months
  FROM ATTRITION_MERCHANT_MONTHLY mm
  JOIN ATTRITION_MERCHANT mer USING (merchant_id)
),
banded AS (
  SELECT
    category_code, category_name, month_end,
    monthly_volume_usd, baseline_monthly_volume, txn_count, support_tickets,
    days_since_last_txn, volume_decline_pct, churned_flag,
    CASE
      WHEN churned_flag                                        THEN 'churned'
      WHEN days_since_last_txn > 45 OR vol_ratio < 0.60        THEN 'at-risk'
      WHEN days_since_last_txn > 20 OR vol_ratio < 0.85        THEN 'watch'
      ELSE 'healthy'
    END AS risk_band,
    CASE
      WHEN tenure_months < 12  THEN 'New (<1yr)'
      WHEN tenure_months < 36  THEN 'Established (1-3yr)'
      ELSE 'Mature (3yr+)'
    END AS tenure_band
  FROM per_merchant
),
agg AS (
  SELECT
    category_code, category_name, month_end, risk_band, tenure_band,
    COUNT(*)                                 AS merchant_count,
    COUNT_IF(NOT churned_flag)               AS active_merchant_count,
    COUNT_IF(churned_flag)                   AS churned_count,
    COUNT_IF(risk_band = 'at-risk')          AS at_risk_count,
    COUNT_IF(risk_band = 'watch')            AS watch_count,
    COUNT_IF(risk_band = 'healthy')          AS healthy_count,
    SUM(monthly_volume_usd)                  AS monthly_volume_usd,
    SUM(baseline_monthly_volume)             AS baseline_volume_usd,
    SUM(txn_count)                           AS txn_count,
    SUM(support_tickets)                     AS support_tickets,
    ROUND(AVG(days_since_last_txn), 1)       AS avg_days_since_last_txn,
    ROUND(AVG(volume_decline_pct), 2)        AS avg_volume_decline_pct,
    ROUND(SUM(monthly_volume_usd) / NULLIF(SUM(baseline_monthly_volume), 0) * 100, 1) AS nrr_pct
  FROM banded
  GROUP BY category_code, category_name, month_end, risk_band, tenure_band
)
SELECT
  a.category_code, a.category_name, a.month_end, a.risk_band, a.tenure_band,
  a.merchant_count, a.active_merchant_count, a.churned_count,
  a.at_risk_count, a.watch_count, a.healthy_count,
  a.monthly_volume_usd, a.baseline_volume_usd, a.txn_count, a.support_tickets,
  a.avg_days_since_last_txn, a.avg_volume_decline_pct, a.nrr_pct,
  ch.market_sales_usd AS category_market_sales_usd,
  ch.mom_growth_pct   AS category_mom_growth_pct,
  ch.yoy_growth_pct   AS category_yoy_growth_pct
FROM agg a
LEFT JOIN ATTRITION_CATEGORY_HEALTH ch
  ON ch.category_code = a.category_code AND ch.month_end = a.month_end;

-- 6. Data-source marker -------------------------------------------------------
CREATE OR REPLACE VIEW ATTRITION_DATA_SOURCE_INFO AS
SELECT 'marketplace' AS mode,
       'Synthetic merchant book contextualized against REAL US Census Advance Retail Sales (free Financial Data Package listing).' AS note;

-- 7. Semantic view (single wide-view over ATTRITION_BENCHMARK) ----------------
CREATE OR REPLACE SEMANTIC VIEW ATTRITION_SV
  TABLES ( ab AS SNOWPACK_MERCHANT_ATTRITION.CORE.ATTRITION_BENCHMARK
             PRIMARY KEY (category_code, month_end, risk_band, tenure_band)
             WITH SYNONYMS = ('merchant attrition','churn early warning','merchant health')
             COMMENT = 'Merchant attrition health by category, month, risk band and tenure band vs category demand' )
  FACTS (
    ab.monthly_volume_usd AS MONTHLY_VOLUME_USD,
    ab.baseline_volume_usd AS BASELINE_VOLUME_USD,
    ab.txn_count AS TXN_COUNT,
    ab.support_tickets AS SUPPORT_TICKETS,
    ab.merchant_count AS MERCHANT_COUNT,
    ab.active_merchant_count AS ACTIVE_MERCHANT_COUNT,
    ab.churned_count AS CHURNED_COUNT,
    ab.at_risk_count AS AT_RISK_COUNT,
    ab.watch_count AS WATCH_COUNT,
    ab.healthy_count AS HEALTHY_COUNT,
    ab.avg_days_since_last_txn AS AVG_DAYS_SINCE_LAST_TXN,
    ab.avg_volume_decline_pct AS AVG_VOLUME_DECLINE_PCT,
    ab.nrr_pct AS NRR_PCT,
    ab.category_market_sales_usd AS CATEGORY_MARKET_SALES_USD,
    ab.category_mom_growth_pct AS CATEGORY_MOM_GROWTH_PCT,
    ab.category_yoy_growth_pct AS CATEGORY_YOY_GROWTH_PCT
  )
  DIMENSIONS (
    ab.category_name AS CATEGORY_NAME WITH SYNONYMS = ('merchant category','vertical','segment') COMMENT = 'Merchant category (MCC-aligned)',
    ab.category_code AS CATEGORY_CODE,
    ab.month_end AS MONTH_END WITH SYNONYMS = ('month','period','as of'),
    ab.report_year AS YEAR(MONTH_END) WITH SYNONYMS = ('year'),
    ab.risk_band AS RISK_BAND WITH SYNONYMS = ('health band','risk segment','merchant health') COMMENT = 'healthy / watch / at-risk / churned',
    ab.tenure_band AS TENURE_BAND WITH SYNONYMS = ('tenure','merchant age','cohort') COMMENT = 'New (<1yr) / Established (1-3yr) / Mature (3yr+)'
  )
  METRICS (
    ab.total_merchants AS SUM(ab.merchant_count) COMMENT = 'Total merchant-months in scope',
    ab.active_merchants AS SUM(ab.active_merchant_count) COMMENT = 'Active (non-churned) merchants',
    ab.churned_merchants AS SUM(ab.churned_count) COMMENT = 'Churned merchants',
    ab.at_risk_merchants AS SUM(ab.at_risk_count) COMMENT = 'At-risk merchants',
    ab.churn_rate_pct AS SUM(ab.churned_count) * 100.0 / NULLIF(SUM(ab.merchant_count), 0) COMMENT = 'Churn rate (% of merchants churned)',
    ab.net_revenue_retention AS SUM(ab.monthly_volume_usd) * 100.0 / NULLIF(SUM(ab.baseline_volume_usd), 0) COMMENT = 'Net revenue retention (% of baseline volume retained)',
    ab.total_volume_usd AS SUM(ab.monthly_volume_usd) COMMENT = 'Total processed volume (USD)',
    ab.total_txns AS SUM(ab.txn_count) COMMENT = 'Total transactions',
    ab.avg_volume_decline AS AVG(ab.avg_volume_decline_pct) COMMENT = 'Average volume decline vs baseline (%)',
    ab.avg_days_idle AS AVG(ab.avg_days_since_last_txn) COMMENT = 'Average days since last transaction',
    ab.category_demand_sales AS AVG(ab.category_market_sales_usd) COMMENT = 'Category market retail sales (USD, non-additive)',
    ab.category_demand_yoy AS AVG(ab.category_yoy_growth_pct) COMMENT = 'Category demand YoY growth (%, non-additive)',
    ab.category_demand_mom AS AVG(ab.category_mom_growth_pct) COMMENT = 'Category demand MoM growth (%, non-additive)'
  )
  COMMENT = 'Merchant attrition early-warning semantic view (synthetic merchant book vs REAL category demand backdrop).';

-- 8. Output table + agent -----------------------------------------------------
CREATE TABLE IF NOT EXISTS ATTRITION_REPORTS (
  run_id STRING DEFAULT UUID_STRING(), subject STRING, draft_md STRING, report_md STRING,
  status STRING, edits_applied INT, residual_hedges INT, created_at TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE AGENT ATTRITION_AGENT
  COMMENT = 'Merchant Attrition Early-Warning agent (Cortex Analyst over ATTRITION_SV)'
  PROFILE = '{"display_name": "Merchant Attrition Agent", "color": "orange"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto
  instructions:
    response: 'You are a payments merchant-retention analyst. Use ONLY figures from the Analyst tool. risk_band is healthy/watch/at-risk/churned; net_revenue_retention and churn_rate_pct are percentages; express USD in $B/$M. Never invent numbers. Be concise, cite the month, and when flagging attrition always contrast merchant decline against the category demand backdrop (category_demand_yoy).'
    orchestration: 'For any churn, attrition, retention, volume-decline, at-risk, or merchant-health question use the MerchantAttrition Analyst tool.'
    sample_questions:
      - question: 'Which categories have the highest at-risk merchant count in 2026, and is their category demand growing or shrinking?'
  tools:
    - tool_spec:
        type: cortex_analyst_text_to_sql
        name: MerchantAttrition
        description: 'Merchant attrition health (churn rate, NRR, at-risk counts, volume decline) by category, month, risk band and tenure vs REAL category demand backdrop.'
  tool_resources:
    MerchantAttrition:
      semantic_view: SNOWPACK_MERCHANT_ATTRITION.CORE.ATTRITION_SV
  $$;
