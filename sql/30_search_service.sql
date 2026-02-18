-- ============================================
-- 30_search_service.sql
-- Cortex Search Service for semantic retrieval
-- ============================================

USE DATABASE PROJECT_DB;
USE SCHEMA SERVICES;
USE WAREHOUSE COMPUTE_WH;

CREATE OR REPLACE CORTEX SEARCH SERVICE support_tickets_search_service
  ON chunk_body
  ATTRIBUTES subject, priority, type, queue, language
  WAREHOUSE = compute_wh
  TARGET_LAG = '1 day'
  EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
  AS (
    SELECT *,
        concat('Body: ', chunk_body, ' \n Answer:', answer) as body_answer
    FROM CURATED.TICKETS
);