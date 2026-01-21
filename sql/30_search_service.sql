-- ============================================
-- 30_search_service.sql
-- Cortex Search Service for semantic retrieval
-- ============================================

USE DATABASE PROJECT_DB;
USE SCHEMA SERVICES;
USE WAREHOUSE COMPUTE_WH;

-- Create Cortex Search Service on KB chunks
-- Adjust columns and attributes based on your schema
/*
CREATE CORTEX SEARCH SERVICE support_tickets_search_service
ON chunk_text
ATTRIBUTES language, product, topic, kb_id
FROM CURATED.KB_CHUNKS;
*/

-- Alternative: Search on KB articles directly (if no chunking)
/*
CREATE CORTEX SEARCH SERVICE support_tickets_search_service
ON body_answer
ATTRIBUTES language, product, topic, kb_id
FROM CURATED.KB_ARTICLES;
*/

-- Test search service (example query)
-- SELECT * FROM TABLE(
--     support_tickets_search_service!SEARCH(
--         query => 'How do I reset my password?',
--         filter => {'language': 'en'},
--         limit => 5
--     )
-- );
