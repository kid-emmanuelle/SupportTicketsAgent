# Support Tickets Agent

A multilingual support ticket processing agent using Snowflake Cortex and LangGraph.

## Overview

This project implements an intelligent agent that:
- Classifies support tickets by topic and intent
- Assigns priority levels (URGENT/HIGH/MEDIUM/LOW)
- Retrieves relevant knowledge base articles using semantic search
- Generates contextual responses
- Applies policy guardrails

## Project Structure

See [docs/Architecture.md](docs/Architecture.md) for detailed architecture and workflow.

```
├── sql/              # Snowflake DDL and setup scripts
├── src/              # Agent library (graph, retrieval, prompts, eval)
├── app/              # Streamlit demo UI
├── scripts/          # CLI entry points
├── notebooks/        # Exploration notebooks
└── tests/            # Unit tests
```

## Setup

1. Copy `.env.example` to `.env` and fill in your Snowflake credentials:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up Snowflake objects:
   ```bash
   # Run SQL scripts in order
   snowsql -f sql/00_setup.sql
   snowsql -f sql/10_ingest.sql
   snowsql -f sql/20_curate.sql
   snowsql -f sql/30_search_service.sql
   ```

4. Load data:
   ```bash
   python scripts/load_data.py
   ```

## Usage

Run agent on a single ticket:
```bash
python scripts/run_agent.py --ticket-id 12345
```

Run batch processing:
```bash
python scripts/run_batch.py --input tickets.csv
```

Launch demo app:
```bash
streamlit run app/streamlit_app.py
```

## Development

Install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

Run tests:
```bash
pytest tests/
```

## Git Workflow

- `main`: stable, demo-ready
- `dev`: integration branch
- Feature branches: `feat/ingest`, `feat/search`, `feat/langgraph`, etc.

**Important:** Never commit `.env` or credentials!

## Evaluation

Run evaluation:
```bash
python src/support_agent/eval/run_eval.py
```

View results in `notebooks/03_eval_report.ipynb`
