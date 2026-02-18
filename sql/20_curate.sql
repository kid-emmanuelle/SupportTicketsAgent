-- ============================================
-- 20_curate.sql
-- Curated tables: cleaned tickets + KB articles
-- ============================================

USE DATABASE PROJECT_DB;
USE SCHEMA CURATED;
USE WAREHOUSE COMPUTE_WH;

DROP TABLE IF EXISTS TICKETS;

-- Curated tickets table
CREATE TABLE IF NOT EXISTS TICKETS (
--    ticket_id VARCHAR PRIMARY KEY,
    language VARCHAR,
    subject VARCHAR,
    chunk_body VARCHAR,
    answer VARCHAR,
--    created_at TIMESTAMP,
--    category VARCHAR,
    priority VARCHAR,
    queue VARCHAR,
    type VARCHAR
--  status VARCHAR,
--  tags ARRAY
--  product VARCHAR,
--  topic VARCHAR
);

-- Example: Populate curated tables from raw
INSERT INTO TICKETS
SELECT
--    'NULL' AS ticket_id,
    language,
    subject,
    LEFT(
        LOWER(TRIM(COALESCE(body, ''))),
        2000
    ) AS chunk_body,
    LOWER(TRIM(COALESCE(answer, ''))) AS answer,
--    created_at,
--    category,
    priority,
    queue,
    type
--  status,
--  'NULL' as tags, -- SPLIT(tags, ',')
--  NULL AS product,
--  NULL AS topic

FROM RAW.SUPPORT_TICKETS
WHERE 
    body IS NOT NULL 
    AND TRIM(body) != ''
    AND answer IS NOT NULL 
    AND TRIM(answer) != ''
;
