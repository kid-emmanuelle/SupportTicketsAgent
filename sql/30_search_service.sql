-- ============================================
-- 30_search_service.sql
-- Cortex Search Service for semantic retrieval
-- ============================================

USE DATABASE PROJECT_DB;
USE SCHEMA SERVICES;
USE WAREHOUSE COMPUTE_WH;

CREATE OR REPLACE CORTEX SEARCH SERVICE PROJECT_DB.SERVICES.support_tickets_search_service
  VECTOR INDEXES REWRITTEN_BODY (model='voyage-multilingual-2')
  ATTRIBUTES PRIORITY, TYPE, LANGUAGE
  WAREHOUSE = compute_wh
  TARGET_LAG = '1 day'
  AS (
    SELECT 
      SUBJECT,
      REWRITTEN_BODY,
      CLEANED_ANSWER,
      TYPE,
      QUEUE,
      PRIORITY,
      LANGUAGE,
      TAG_1,
      TAG_2
    FROM PROJECT_DB.CURATED.TICKETS_CLEANED
);