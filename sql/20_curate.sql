-- ============================================
-- 20_curate.sql
-- Curated tables: cleaned tickets + KB articles
-- ============================================

USE DATABASE PROJECT_DB;
USE SCHEMA CURATED;
USE WAREHOUSE COMPUTE_WH;

-- Curated tickets table
CREATE TABLE IF NOT EXISTS TICKETS (
--    ticket_id VARCHAR PRIMARY KEY,
    language VARCHAR,
    subject VARCHAR,
    body VARCHAR,
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

-- Knowledge base articles (historical solutions)
-- CREATE TABLE IF NOT EXISTS KB_ARTICLES (
--     kb_id VARCHAR PRIMARY KEY,
--     source_ticket_id VARCHAR,
--     title VARCHAR,
--     body_question VARCHAR,
--     body_answer VARCHAR,
--     language VARCHAR,
--     product VARCHAR,
--     topic VARCHAR,
--     created_at TIMESTAMP,
--     metadata VARIANT
-- );

-- -- Optional: Chunked KB for long articles
-- CREATE TABLE IF NOT EXISTS KB_CHUNKS (
--     chunk_id VARCHAR PRIMARY KEY,
--     kb_id VARCHAR,
--     chunk_text VARCHAR,
--     chunk_index INTEGER,
--     language VARCHAR,
--     product VARCHAR,
--     topic VARCHAR,
--     metadata VARIANT,
--     FOREIGN KEY (kb_id) REFERENCES KB_ARTICLES(kb_id)
-- );

-- Example: Populate curated tables from raw
INSERT INTO TICKETS
SELECT
--    'NULL' AS ticket_id,
    language,
    subject,
    body,
    answer,
--    created_at,
--    category,
    priority,
    queue,
    type
--  status,
--  'NULL' as tags, -- SPLIT(tags, ',')
--  NULL AS product,
--  NULL AS topic

FROM RAW.SUPPORT_TICKETS;