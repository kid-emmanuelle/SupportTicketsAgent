PYTHON := $(shell command -v python3 2> /dev/null || command -v python 2> /dev/null)
PIP := $(shell command -v pip3 2> /dev/null || command -v pip 2> /dev/null)

.PHONY: help setup install install-dev load-data build-search build-agent evaluate-agent test clean app full-setup show-env

help:
	@echo "Available commands:"
	@echo "  make full-setup     - Run complete setup pipeline"
	@echo "  make install        - Install dependencies"
	@echo "  make install-dev    - Install dev dependencies"
	@echo "  make setup          - Run Snowflake setup scripts"
	@echo "  make load-data      - Load data into Snowflake"
	@echo "  make build-search   - Build curated table and search service"
	@echo "  make build-agent    - Create Cortex Agent"
	@echo "  make evaluate-agent - Evaluate current agent workflow on curated sample" 
	@echo "  make test           - Run tests"
	@echo "  make app            - Launch Streamlit app"
	@echo "  make clean          - Clean temporary files"
	@echo "  make show-env       - Show detected Python and pip commands"
	

full-setup: install setup load-data build-search build-agent evaluate-agent
	@echo "SupportTicket Agent is ready to use !"

install:
	$(PIP) install -r requirements.txt

install-dev:
	$(PIP) install -r requirements-dev.txt

setup:
	$(PYTHON) -m scripts.setup

load-data:
	$(PYTHON) -m scripts.load_data
	$(PYTHON) -m scripts.process_data

build-search:
	$(PYTHON) -m scripts.build_search

build-agent:
	$(PYTHON) -m scripts.build_agent

evaluate-agent:
	$(PYTHON) -m scripts.evaluate

test:
	pytest tests/ -v

app:
	streamlit run app/streamlit_app.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete
	snowsql -f sql/99_cleanup.sql

show-env:
	@echo "Detected Python: $(PYTHON)"
	@echo "Detected PIP: $(PIP)"