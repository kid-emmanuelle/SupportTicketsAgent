.PHONY: help setup install test clean run-agent run-batch app

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make install-dev   - Install dev dependencies"
	@echo "  make setup         - Run Snowflake setup scripts"
	@echo "  make load-data     - Load data into Snowflake"
	@echo "  make test          - Run tests"
	@echo "  make run-agent     - Run agent on sample ticket"
	@echo "  make run-batch     - Run batch processing"
	@echo "  make app           - Launch Streamlit app"
	@echo "  make clean         - Clean temporary files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

setup:
	@echo "Running Snowflake setup scripts..."
	snowsql -f sql/00_setup.sql
	snowsql -f sql/10_ingest.sql
	snowsql -f sql/20_curate.sql
	snowsql -f sql/30_search_service.sql

load-data:
	python scripts/load_data.py

test:
	pytest tests/ -v

run-agent:
	python scripts/run_agent.py --ticket-id 1

run-batch:
	python scripts/run_batch.py

app:
	streamlit run app/streamlit_app.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
