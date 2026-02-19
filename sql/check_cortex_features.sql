-- ============================================
-- Check Cortex Agents & Threads API availability
-- ============================================

-- 1. Check your Snowflake edition and region
SELECT CURRENT_REGION() AS REGION, 
       CURRENT_VERSION() AS VERSION,
       CURRENT_ACCOUNT() AS ACCOUNT;

-- 2. Check if Cortex Search is available (prerequisite)
SHOW CORTEX SEARCH SERVICES;

-- 3. Try to list your agents (should work even without Threads)
SHOW CORTEX AGENTS IN ACCOUNT;

-- 4. Check your role privileges
SHOW GRANTS TO ROLE ACCOUNTADMIN;

-- 5. Check if you have any existing Cortex functions access
SELECT SNOWFLAKE.CORTEX.COMPLETE('llama3.1-8b', 'test') AS test_completion;

-- 6. Check available Cortex features
SELECT * FROM INFORMATION_SCHEMA.FUNCTIONS 
WHERE FUNCTION_SCHEMA = 'CORTEX' 
LIMIT 10;
