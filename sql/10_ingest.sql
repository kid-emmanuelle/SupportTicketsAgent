-- ============================================
-- 10_ingest.sql
-- Data ingestion: Stage + Raw table + COPY INTO
-- ============================================
USE DATABASE PROJECT_DB;
USE SCHEMA RAW;
USE WAREHOUSE COMPUTE_WH;

-- Create raw table (adjust columns based on your dataset)
CREATE TABLE IF NOT EXISTS SUPPORT_TICKETS (
    SUBJECT VARCHAR,
	BODY VARCHAR,
	ANSWER VARCHAR,
	TYPE VARCHAR,
	QUEUE VARCHAR,
	PRIORITY VARCHAR,
	LANGUAGE VARCHAR,
	VERSION NUMBER,
	TAG_1 VARCHAR,
	TAG_2 VARCHAR,
	TAG_3 VARCHAR,
	TAG_4 VARCHAR,
	TAG_5 VARCHAR,
	TAG_6 VARCHAR,
	TAG_7 VARCHAR,
	TAG_8 VARCHAR
);

-- Load data from stage into table
COPY INTO SUPPORT_TICKETS
FROM @support_data_stage/tickets_clean.csv.gz
FILE_FORMAT = (FORMAT_NAME = 'csv_format')
;
