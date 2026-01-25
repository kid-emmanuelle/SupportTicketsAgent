-- ============================================
-- 00_setup.sql
-- Foundation: Database, Schemas, Warehouse, Stage
-- ============================================

-- Create database
CREATE DATABASE IF NOT EXISTS PROJECT_DB;
USE DATABASE PROJECT_DB;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS CURATED;
CREATE SCHEMA IF NOT EXISTS SERVICES;
CREATE SCHEMA IF NOT EXISTS EVAL;
CREATE SCHEMA IF NOT EXISTS APP;

-- Create warehouse
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WITH WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

-- Set defaults
USE WAREHOUSE COMPUTE_WH;
USE SCHEMA RAW;

-- Grant permissions (adjust role as needed)
-- GRANT USAGE ON DATABASE PROJECT_DB TO ROLE YOUR_ROLE
-- GRANT USAGE ON ALL SCHEMAS IN DATABASE PROJECT_DB TO ROLE YOUR_ROLE
-- GRANT ALL ON WAREHOUSE COMPUTE_WH TO ROLE YOUR_ROLE

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

SELECT 'Setup complete: Database, Schemas, and Warehouse created.' AS STATUS;

