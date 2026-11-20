-- ============================================================================
-- Merchant Attrition Early-Warning — teardown.sql
-- ----------------------------------------------------------------------------
-- Removes everything this pack creates: the dedicated database (all tables,
-- views, semantic view, agent, and output table in SNOWPACK_MERCHANT_ATTRITION.CORE)
-- and the dedicated warehouse. Safe to re-run.
-- ============================================================================

DROP DATABASE IF EXISTS SNOWPACK_MERCHANT_ATTRITION;
DROP WAREHOUSE IF EXISTS SNOWPACK_MERCHANT_ATTRITION_WH;
