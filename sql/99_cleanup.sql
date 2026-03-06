-- ============================================
-- 99_cleanup.sql
-- Optional: Drop all objects for fresh start
-- USE WITH CAUTION!
-- ============================================

-- Uncomment to drop everything

USE ROLE SYSADMIN;

DROP CORTEX SEARCH SERVICE IF EXISTS PROJECT_DB.SERVICES.support_tickets_search_service;
DROP AGENT IF EXISTS PROJECT_DB.APP.support_tickets_agent;
DROP DATABASE IF EXISTS PROJECT_DB CASCADE;
DROP WAREHOUSE IF EXISTS COMPUTE_WH;
