# Support Tickets Agent

A multilingual support ticket processing agent using Snowflake Cortex and LangGraph.

## Overview

This project implements an intelligent agent that:
- Classifies support tickets by topic and intent
- Assigns priority levels (URGENT/HIGH/MEDIUM/LOW)
- Retrieves relevant knowledge base articles using semantic search
- Generates contextual responses
- Agent's responses evaluation with llm as a judge
- Applies policy guardrails

## Project Structure

See [docs/Architecture.md](docs/Architecture.md) for detailed architecture and workflow.

```
├── sql/              # Snowflake DDL
├── src/              # Agent library (graph, retrieval, prompts, eval, cortex_agent, persistence)
├── app/              # Streamlit demo UI
├── scripts/          # Setup python scripts
├── notebooks/        # Exploration notebooks
└── tests/            # Unit tests
```

## Setup

1. Set environment:
   ```bash
   cd ./SupportTicketsAgent
   py -3.11 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```
2. Launch setup with makefile:
   ```bash
   make full-setup
   ```
3. Launch app:
   ```bash
   make app
   ```

4. Enjoy our agent !

## Development

Install dev dependencies:
```bash
make install-dev
```

Run tests:
```bash
pytest tests/
```

## Usage

Launch demo app:
```bash
streamlit run app/streamlit_app.py
```

## Git Workflow

- `main`: stable, demo-ready
- Feature branches: `feat/ingest`, `feat-search-service`, `feat/langgraph`, etc.

**Important:** Never commit `.env` or credentials!

## Evaluation

You can configure evaluation sample on ```EVALUATION_CONFIG``` stored in ```scripts/evaluate.py```
```bash
make evaluate-agent
```
View results in `notebooks/03_eval_report.ipynb`

# Démo : 

We will demonstrate here with screenshots the different features of the service used by the client.
We will follow this scenario:
- Interface at opening
- 2-3 question conversation
- New conversation
- Switching/Resuming conversation

When opening the application, the client finds a chat system with the ability to converse with the RAG but also to find their other conversations.

![Interface at Opening](img/welcome_ui.png)

We can see that the agent leverages the search service with the knowledge base to best answer the user's question.

![Conversation 1 question 1](img/example_conv1_q1.png)

We can also continue the conversation with other questions or requests.

![Conversation 1 question 2](img/example_conv1_q2.png)

We can also converse in another chat in German, for example.

![New Conversation 2 ](img/example_conv2.png)

The client can retrieve their old conversations; here we see the first conversation. The context is also preserved and reused by the agent throughout a conversation.

![Reload Conversation 1](img/example_conv1_reloading.png)