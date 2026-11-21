-- ============================================================================
-- Merchant Attrition Early-Warning - sql/cleanup.sql
-- Removes everything sql/setup.sql created: the database (tables, views,
-- semantic view, agent, stage, Streamlit app), the warehouse and the role.
-- Objects are owned by MERCHANT_ATTRITION_ROLE, so they are dropped as that
-- role first; ACCOUNTADMIN then drops the role. Run it as the user who ran
-- setup. Safe to re-run: if the role is already gone, start from the
-- USE ROLE ACCOUNTADMIN line.
-- ============================================================================
USE ROLE MERCHANT_ATTRITION_ROLE;  -- granted to the user who ran setup
DROP DATABASE IF EXISTS SNOWPACK_MERCHANT_ATTRITION;
DROP WAREHOUSE IF EXISTS SNOWPACK_MERCHANT_ATTRITION_WH;
USE ROLE ACCOUNTADMIN;
DROP ROLE IF EXISTS MERCHANT_ATTRITION_ROLE;
SHOW DATABASES LIKE 'SNOWPACK_MERCHANT_ATTRITION';
