# Snowflake + LangGraph project workflow

ingest → search/RAG → agent graph → evaluation → app

## Project structure and workflow (Snowflake + LangGraph)
Think of it as 6 layers. Each layer produces artifacts (tables/services/code) that the next layer uses.

### 0. Foundations (once)
**Goal:** consistent environments + permissions.

- Snowflake objects:
    - `PROJECT_DB`
    - Schemas: `RAW`, `CURATED`, `SERVICES`, `EVAL`, `APP`
    - Warehouse: `COMPUTE_WH`

- Secrets/config:
    - connection info + Snowflake Cortex endpoint in `.env` (never committed)

### 1. Data ingestion
**Goal:** land the dataset exactly once and make it reproducible.
1. Put CSV in a Snowflake stage (internal stage or external).
2. Copy it into `RAW.SUPPORT_TICKETS` (raw columns as-is).
3. Basic QA queries (row counts, null checks).

**Output:** `RAW.SUPPORT_TICKETS`

### 2. Curation + chunking (prepare for retrieval)
**Goal:** create clean fields and a “knowledge base” that Search can index.

Typical curated tables:
- `CURATED.TICKETS`
    - ticket_id, language, subject, body, created_at, tags...
- `CURATED.KB_ARTICLES` (or “historical solutions”)
    - kb_id, source_ticket_id, body_question, body_answer, language, product, topic, ...

Optional (but recommended): create a “chunked” table if your answers are long:
- `CURATED.KB_CHUNKS`
    - chunk_id, kb_id, chunk_text, language, metadata_json

**Output:** curated tables, clean text columns

### 3. Retrieval (Cortex Search service)

**Goal:** Snowflake-native semantic search over your KB.

Create a Cortex Search service on `KB_CHUNKS.chunk_text` (or `KB_ARTICLES.body_answer` if short), with filterable attributes like `language`, `product`, `topic`.

Python tool `(retrieve(query))` hits this service and returns top-k chunks.

**Output:** `SERVICES.support_tickets_search_service`

### 4. Agent workflow (LangGraph)

**Goal:** deterministic, grade-friendly pipeline.

A solid “course project” graph (example):
1. ingest_request (normalize input, detect language if needed)
2. classify (topic + intent: bug / request / billing / login / how-to)
3. priority (URGENT/HIGH/MEDIUM/LOW)
4. retrieve (Cortex Search, filtered by language/topic)
5. draft_response (LLM with retrieved context)
6. policy_guardrails (tone, no hallucination claims, add escalation text if urgent)
7. write_back (store in Snowflake: outputs + retrieved ids + timestamps)

**Output:** runnable agent as a Python package + `APP.AGENT_OUTPUTS` table

### 5. Evaluation (offline + stored in Snowflake)

**Goal:** show you measured quality, not just “it works”.

Recommended eval set:
- stratified sample across languages + categories.

Store runs:
- `EVAL.RUNS` (run_id, commit_sha, model, date)
- `EVAL.RESULTS` (run_id, ticket_id, priority_pred, response, retrieved_ids, scores...)

Metrics (pick a few in these options - we can discuss later):
- Retrieval relevance (LLM judge or simple heuristics)
- Response helpfulness (LLM judge rubric)
- Hallucination/grounding (judge: “is it supported by context?”)
- Priority accuracy vs label if you have one (or weak labels)

**Output:** Snowflake tables + a notebook/script that generates a final report of evaluation

### 6. Demo app
**Goal:** easy presentation.
- Streamlit in Snowflake or a minimal local Streamlit that calls agent (simple, i'm too lazy to work on frontend in this project).
- One text box → “Run Agent” → show priority, retrieved snippets, response, and “write ticket” action.

## Git repo structure
```pgsql
SupportTicketsAgent/
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ .env.example                   # template only (never push secrets !!!)
├─ Makefile                       # optional: common commands
│
├─ sql/
│  ├─ 00_setup.sql                # db/schema/roles/warehouse (if allowed)
│  ├─ 10_ingest.sql               # stage + file formats + COPY INTO raw
│  ├─ 20_curate.sql               # curated tables/views
│  ├─ 30_search_service.sql       # CREATE CORTEX SEARCH SERVICE
│  ├─ 40_eval_tables.sql          # eval schema + tables
│  └─ 99_cleanup.sql              # optional
│
├─ src/
│  └─ support_agent/
│     ├─ __init__.py
│     ├─ config.py                # reads env vars, Snowflake connection
│     ├─ snowflake_client.py      # session/root helpers
│     ├─ retrieval.py             # Cortex Search wrapper
│     ├─ prompts/
│     │  ├─ priority.txt
│     │  ├─ classify.txt
│     │  └─ response.txt
│     ├─ graph/
│     │  ├─ state.py              # TypedDict/Pydantic state
│     │  ├─ nodes.py              # node functions
│     │  └─ build.py              # constructs/compiles the graph
│     ├─ persistence/
│     │  └─ writeback.py          # writes outputs to Snowflake tables
│     └─ eval/
│        ├─ run_eval.py           # batch runs
│        └─ scoring.py            # metrics + judge prompts
│
├─ notebooks/
│  ├─ 01_explore_dataset.ipynb
│  ├─ 02_build_search.ipynb
│  └─ 03_eval_report.ipynb
│
├─ app/
│  └─ streamlit_app.py            # demo UI (can work directly on Snowflake)
│
├─ scripts/
│  ├─ load_data.py                # pushes csv to stage, triggers ingest
│  ├─ run_agent.py                # CLI: run one ticket
│  └─ run_batch.py                # CLI: run many tickets
│
└─ tests/
   ├─ test_retrieval.py           # mocks + sanity checks
   ├─ test_graph.py
   └─ test_prompts.py
```

### What goes where (Important !!! - Specially for Jewin)
- `sql/`: everything needed to reproduce Snowflake objects (tables + search service).
- `src/`: the actual agent library (graph, retrieval, prompts, writeback, eval).
- `app/`: demo UI (optional - because we can work directly on Snowflake).
- `scripts/`: runnable entry points (local CLI).
- `notebooks/`: exploration only (don’t make notebooks your production pipeline).

### Git workflow for collaboration (Jewin !!!)

#### Branching
- `main`: always stable, demo-ready
- `dev`: integration branch
- feature branches:
    - `feat-ingest`
    - `feat-search`
    - `feat-langgraph`
    - `feat-eval`
    - `feat-app`
    - 
#### Rules that save our life
- Never commit `.env` or credentials
- Every PR must:
    - run `scripts/run_agent.py` on a sample ticket
    - not break `sql/` reproducibility
      search_service: added init curated table creation, insert and search service creation. Notebook build search using to test
- Before commit, always run ruff:
  ```bash
  ruff check --fix [path]   # Lint and auto-fix
  ruff format [path]        # Format code
  ```
  Where `[path]` is optional: a file, folder, or omit for current directory.

  Examples:
  ```bash
  ruff check --fix              # All files
  ruff check --fix src/         # Only src folder
  ruff format src/support_agent/config.py  # Single file
  ```