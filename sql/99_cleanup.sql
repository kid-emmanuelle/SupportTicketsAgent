-- ============================================
-- 99_cleanup.sql
-- Optional: Drop all objects for fresh start
-- USE WITH CAUTION!
-- ============================================

-- Uncomment to drop everything
/*
USE ROLE SYSADMIN;

DROP CORTEX SEARCH SERVICE IF EXISTS PROJECT_DB.SERVICES.support_tickets_search_service;
DROP DATABASE IF EXISTS PROJECT_DB CASCADE;
DROP WAREHOUSE IF EXISTS COMPUTE_WH;
*/

-- To drop individual schemas only:
/*
USE DATABASE PROJECT_DB;
DROP SCHEMA IF EXISTS APP CASCADE;
DROP SCHEMA IF EXISTS EVAL CASCADE;
DROP SCHEMA IF EXISTS SERVICES CASCADE;
DROP SCHEMA IF EXISTS CURATED CASCADE;
DROP SCHEMA IF EXISTS RAW CASCADE;
*/
