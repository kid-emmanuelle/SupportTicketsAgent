-- ============================================
-- 10_ingest.sql
-- Data ingestion: Stage + Raw table + COPY INTO
-- ============================================

USE DATABASE PROJECT_DB;
USE SCHEMA RAW;
USE WAREHOUSE COMPUTE_WH;

-- Create internal stage for CSV files
CREATE STAGE IF NOT EXISTS support_data_stage;

-- Create file format for CSV
CREATE OR REPLACE FILE FORMAT csv_format
    TYPE = 'CSV'
    FIELD_DELIMITER = ','
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    NULL_IF = ('NULL', 'null', '');

-- Create raw table (adjust columns based on your dataset)
CREATE TABLE IF NOT EXISTS SUPPORT_TICKETS (
    ticket_id VARCHAR,
    created_at TIMESTAMP,
    language VARCHAR,
    subject VARCHAR,
    body VARCHAR,
    category VARCHAR,
    priority VARCHAR,
    status VARCHAR,
    tags VARCHAR,
    metadata VARIANT
);

-- Example COPY INTO command (run after uploading file to stage)
-- PUT file://path/to/tickets.csv @support_data_stage AUTO_COMPRESS=TRUE;
-- COPY INTO SUPPORT_TICKETS
-- FROM @support_data_stage/tickets.csv
-- FILE_FORMAT = (FORMAT_NAME = 'csv_format')
-- ON_ERROR = 'CONTINUE';

-- Basic QA queries
-- SELECT COUNT(*) FROM SUPPORT_TICKETS;
-- SELECT * FROM SUPPORT_TICKETS LIMIT 10;
