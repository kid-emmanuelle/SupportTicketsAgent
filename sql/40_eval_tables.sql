-- ============================================
-- 40_eval_tables.sql
-- Evaluation schema and result storage
-- ============================================

USE DATABASE PROJECT_DB;
USE SCHEMA EVAL;
USE WAREHOUSE COMPUTE_WH;

-- Evaluation runs metadata
CREATE TABLE IF NOT EXISTS RUNS (
    run_id VARCHAR PRIMARY KEY,
    commit_sha VARCHAR,
    model VARCHAR,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    config VARIANT,
    notes VARCHAR
);

-- Evaluation results per ticket
CREATE TABLE IF NOT EXISTS RESULTS (
    result_id VARCHAR PRIMARY KEY,
    run_id VARCHAR,
    ticket_id VARCHAR,
    priority_pred VARCHAR,
    category_pred VARCHAR,
    response_generated VARCHAR,
    retrieved_ids ARRAY,
    retrieval_score FLOAT,
    response_helpfulness_score FLOAT,
    hallucination_score FLOAT,
    overall_score FLOAT,
    eval_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    FOREIGN KEY (run_id) REFERENCES RUNS(run_id)
);

-- Optional: Ground truth labels for evaluation
CREATE TABLE IF NOT EXISTS GROUND_TRUTH (
    ticket_id VARCHAR PRIMARY KEY,
    true_priority VARCHAR,
    true_category VARCHAR,
    expected_response_quality VARCHAR,
    annotator VARCHAR,
    annotation_date TIMESTAMP
);
