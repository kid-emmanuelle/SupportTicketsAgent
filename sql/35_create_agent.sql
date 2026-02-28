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
    orchestration: claude-4-sonnet

  orchestration:
    budget:
      seconds: 120
      tokens: 20000

  instructions:
    response: |
      You are a helpful customer support agent.
      Respond concisely, with clear steps, and ask one clarifying question when needed.
      Always cite the source ticket information when providing answers.
    orchestration: |
      Use search_tool whenever you need to find relevant support tickets or policy context.
      The search_tool searches through historical support tickets (CLEANED_ANSWER, SUBJECT, REWRITTEN_BODY, TAG_1, TAG_2).
      Always specify columns field with CLEANED_ANSWER included when doing a request to search_tool.
      If no relevant context is found, respond with best-effort guidance and ask for details.
      Prioritize answers from tickets with similar type, priority, and language.
    system: |
      You assist users with troubleshooting and account/product questions.
      Do not invent internal policies; prefer grounded answers from the knowledge base.
      You have access to historical support tickets through the search tool.
  
  tools:
    - tool_spec:
        type: cortex_search
        name: search_tool
        description: |
          Searches the support tickets knowledge base containing historical customer issues and resolutions.
          The search covers ticket subjects, bodies (rewritten for clarity), answers, and metadata (type, priority, language, queue, tags).
          Use this tool to find similar past issues and their solutions. 
          When calling this tool, specify columns output (cleaned_answer, type, queue, priority, subject) to get full search service output capability.
          Example: {query: Database optimization, columns: [CLEANED_ANSWER, TYPE, PRIORITY, LANGUAGE, SUBJECT], limit: 10}
        input_schema:
          type: object
          properties:
            query:
              type: string
              description: The search query text to find relevant support tickets based on customer issues
            columns:
              type: object
              description: Specify output columns to get from search result, always include CLEANED_ANSWER
              properties:
                CLEANED_ANSWER:
                  type: string
                  description: answer of the ticket
                SUBJECT:
                  type: string
                  description: subject of the ticket, can have empty value
                REWRITTEN_BODY:
                  type: string
                  description: body of the ticket also used to as vector search 
                TYPE:
                  type: string
                  description: ticket type (incident, request, change, problem)
                QUEUE:
                  type: string
                  description: ticket queue (Technical Support, Product Support, Customer Service, IT Support, Sales and Pre-Sales, General Inquiry, ...)
                PRIORITY:
                  type: string
                  description: ticket priority (high, medium, low)
                LANGUAGE:
                  type: string
                  description: ticket body and answer language (en, fr, es, de)
                TAG_1:
                  type: string
                  description: ticket additional tag (billing, bug, ...)
                TAG_2:
                  type: string
                  description: ticket additional tag (billing, bug, ...)

            filters:
              type: object
              description: Optional filters to narrow down search results by metadata
              properties:
                PRIORITY:
                  type: string
                  description: Filter by ticket priority (e.g., high, medium, low)
                TYPE:
                  type: string
                  description: Filter by ticket type (incident, request, change, problem)
                LANGUAGE:
                  type: string
                  description: Filter by ticket language (e.g., en, fr, es, de)
            limit:
              type: integer
              description: Maximum number of results to return (default is 5, max is 10)
              default: 5
          required:
            - query
            - columns

  tool_resources:
    search_tool:
      search_service: PROJECT_DB.SERVICES.support_tickets_search_service
      title_column: CLEANED_ANSWER
      id_column: SUBJECT
      max_results: 5
  $$;