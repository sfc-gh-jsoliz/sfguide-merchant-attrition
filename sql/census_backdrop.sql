-- ============================================================================
-- Merchant Attrition Early-Warning - sql/census_backdrop.sql  (optional)
-- ----------------------------------------------------------------------------
-- Swaps the synthetic category demand backdrop for REAL US Census Advance
-- Retail Sales (seasonally adjusted, USD) from the free Snowflake Marketplace
-- "Financial Data Package" (SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE).
-- The merchant book stays synthetic: a specific acquirer's merchant-level
-- volume has no public source.
--
-- Prereqs: run sql/setup.sql first, then get the free Financial Data Package
-- listing in Snowsight > Marketplace and grant the pack role access to it:
--   GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE_PUBLIC_DATA_FINANCIAL_PACKAGE
--     TO ROLE MERCHANT_ATTRITION_ROLE;
-- Undo: re-run sql/setup.sql (it recreates the synthetic backdrop view).
-- This script is the original pack's real-data query; it was not re-run in the
-- v2 live verification (see README, Known limitations).
-- ============================================================================
USE ROLE MERCHANT_ATTRITION_ROLE;
USE WAREHOUSE SNOWPACK_MERCHANT_ATTRITION_WH;
USE SCHEMA SNOWPACK_MERCHANT_ATTRITION.CORE;

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

CREATE OR REPLACE VIEW ATTRITION_DATA_SOURCE_INFO AS
SELECT 'marketplace' AS mode,
       'Synthetic merchant book contrasted with REAL US Census Advance Retail Sales (free Financial Data Package listing).' AS note;

SELECT category_code, MAX(month_end) AS latest_month FROM ATTRITION_CATEGORY_HEALTH GROUP BY category_code ORDER BY 1;
