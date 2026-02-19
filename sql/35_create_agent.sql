-- ============================================
-- 35_create_agent.sql
-- Create a Cortex Agent object for this project
-- ============================================

USE DATABASE PROJECT_DB;
USE SCHEMA APP;

-- This agent is designed for threaded conversations via the Cortex Agents Run API.
-- It references the Cortex Search service created in sql/30_search_service.sql.

CREATE OR REPLACE AGENT support_tickets_agent
  COMMENT = 'Support tickets agent (Cortex Agents) for SupportTicketsAgent project'
  PROFILE = '{"display_name": "Support Tickets Agent", "color": "blue"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto

  orchestration:
    budget:
      seconds: 60
      tokens: 12000

  instructions:
    response: |
      You are a helpful customer support agent.
      Respond concisely, with clear steps, and ask one clarifying question when needed.
    orchestration: |
      Use search_tool whenever you need product or policy context.
      If no relevant context is found, respond with best-effort guidance and ask for details.
    system: |
      You assist users with troubleshooting and account/product questions.
      Do not invent internal policies; prefer grounded answers.

  tools:
    - tool_spec:
        type: "cortex_search"
        name: "search_tool"
        description: "Searches the support knowledge base"

  tool_resources:
    search_tool:
      name: "PROJECT_DB.SERVICES.support_tickets_search_service"
      max_results: "5"
  $$;

-- Optional grants (adjust role)
-- GRANT USAGE ON AGENT PROJECT_DB.APP.support_tickets_agent TO ROLE YOUR_ROLE;
