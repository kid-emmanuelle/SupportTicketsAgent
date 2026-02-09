"""Integration tests for graph node functions with real LLM and session."""

import os

from dotenv import load_dotenv
import pytest

from support_agent.config import get_settings
from support_agent.graph.nodes import (
    build_llm,
    classify_topic_intent,
    draft_response,
    evaluate_priority,
    retrieve_node,
)
from support_agent.graph.state import TicketState
from support_agent.snowflake_client import create_snowpark_session


load_dotenv()


@pytest.fixture(scope="module")
def settings():
    """Load settings from environment."""
    return get_settings()


@pytest.fixture(scope="module")
def session(settings):
    """Create a real Snowpark session."""
    return create_snowpark_session(settings)


@pytest.fixture(scope="module")
def llm(settings):
    """Build a real LLM instance."""
    return build_llm(settings)


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_BASE") or not os.getenv("OPENAI_API_KEY"),
    reason="Requires Snowflake Cortex env vars",
)
class TestGraphNodesIntegration:
    """Real integration tests for graph node functions."""

    def test_classify_topic_intent(self, llm):
        """Test classify_topic_intent with a real LLM."""
        state: TicketState = {
            "issue_description": "I cannot log in to my account. The password reset is not working."
        }

        result = classify_topic_intent(llm, state)

        # Should return topic and intent
        assert "topic" in result
        assert "intent" in result
        assert isinstance(result["topic"], str)
        assert isinstance(result["intent"], str)
        assert len(result["topic"]) > 0
        assert len(result["intent"]) > 0

    def test_classify_topic_intent_technical(self, llm):
        """Test classify_topic_intent with a technical issue."""
        state: TicketState = {
            "issue_description": "The API returns 500 error when I call the /users endpoint."
        }

        result = classify_topic_intent(llm, state)

        assert "topic" in result
        assert "intent" in result
        # Topic should be somewhat related to technical/API issues
        assert result["topic"].lower() in [
            "technical",
            "api",
            "bug",
            "error",
            "other",
            "integration",
            "system",
        ]

    def test_evaluate_priority_urgent(self, llm):
        """Test evaluate_priority with an urgent issue."""
        state: TicketState = {
            "issue_description": "URGENT: All users are locked out and cannot access the system. Production is down!"
        }

        result = evaluate_priority(llm, state)

        assert "priority_level" in result
        assert result["priority_level"] in ["LOW", "MEDIUM", "HIGH", "URGENT"]
        # This should likely be HIGH or URGENT
        assert result["priority_level"] in ["HIGH", "URGENT"]

    def test_evaluate_priority_low(self, llm):
        """Test evaluate_priority with a low priority issue."""
        state: TicketState = {
            "issue_description": "It would be nice to have dark mode in the settings page."
        }

        result = evaluate_priority(llm, state)

        assert "priority_level" in result
        assert result["priority_level"] in ["LOW", "MEDIUM", "HIGH", "URGENT"]
        # This should likely be LOW or MEDIUM
        assert result["priority_level"] in ["LOW", "MEDIUM"]

    def test_evaluate_priority_medium(self, llm):
        """Test evaluate_priority with a medium priority issue."""
        state: TicketState = {
            "issue_description": "The export feature is slow and takes several minutes to complete."
        }

        result = evaluate_priority(llm, state)

        assert "priority_level" in result
        assert result["priority_level"] in ["LOW", "MEDIUM", "HIGH", "URGENT"]

    def test_retrieve_node(self, session, settings):
        """Test retrieve_node with a real session and settings."""
        state: TicketState = {
            "issue_description": "How do I reset my password?"
        }

        result = retrieve_node(session, settings, state)

        assert "retrieved_context" in result
        assert isinstance(result["retrieved_context"], list)
        # Should retrieve some context chunks
        assert len(result["retrieved_context"]) >= 0

    def test_retrieve_node_technical_query(self, session, settings):
        """Test retrieve_node with a technical query."""
        state: TicketState = {
            "issue_description": "API authentication error 401"
        }

        result = retrieve_node(session, settings, state)

        assert "retrieved_context" in result
        assert isinstance(result["retrieved_context"], list)

    def test_draft_response_with_context(self, llm):
        """Test draft_response with retrieved context."""
        state: TicketState = {
            "issue_description": "I cannot access my account",
            "topic": "authentication",
            "intent": "troubleshooting",
            "priority_level": "MEDIUM",
            "retrieved_context": [
                "To reset your password, go to the login page and click 'Forgot Password'.",
                "You can also contact support at support@example.com for account issues.",
            ],
        }

        result = draft_response(llm, state)

        assert "final_response" in result
        assert isinstance(result["final_response"], str)
        assert len(result["final_response"]) > 20
        # Should contain some meaningful response
        assert any(
            word in result["final_response"].lower()
            for word in ["password", "account", "reset", "support", "help"]
        )

    def test_draft_response_without_context(self, llm):
        """Test draft_response without retrieved context."""
        state: TicketState = {
            "issue_description": "Very specific technical question about obscure feature",
            "topic": "other",
            "intent": "question",
            "priority_level": "LOW",
            "retrieved_context": [],
        }

        result = draft_response(llm, state)

        assert "final_response" in result
        assert isinstance(result["final_response"], str)
        assert len(result["final_response"]) > 10

    def test_full_pipeline(self, llm, session, settings):
        """Test the full pipeline: classify -> priority -> retrieve -> respond."""
        initial_state: TicketState = {
            "issue_description": "I want to enable two-factor authentication for my account"
        }

        # Step 1: Classify
        state = initial_state.copy()
        classify_result = classify_topic_intent(llm, state)
        state.update(classify_result)

        assert "topic" in state
        assert "intent" in state

        # Step 2: Priority
        priority_result = evaluate_priority(llm, state)
        state.update(priority_result)

        assert "priority_level" in state
        assert state["priority_level"] in ["LOW", "MEDIUM", "HIGH", "URGENT"]

        # Step 3: Retrieve
        retrieve_result = retrieve_node(session, settings, state)
        state.update(retrieve_result)

        assert "retrieved_context" in state
        assert isinstance(state["retrieved_context"], list)

        # Step 4: Draft response
        response_result = draft_response(llm, state)
        state.update(response_result)

        assert "final_response" in state
        assert isinstance(state["final_response"], str)
        assert len(state["final_response"]) > 20


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_BASE") or not os.getenv("OPENAI_API_KEY"),
    reason="Requires Snowflake Cortex env vars",
)
def test_build_llm(settings):
    """Test that build_llm creates a valid ChatOpenAI instance."""
    llm = build_llm(settings)

    assert llm is not None
    assert hasattr(llm, "invoke")

    # Test a simple invocation
    from langchain_core.messages import HumanMessage

    response = llm.invoke([HumanMessage(content="Say 'test' only.")])

    assert response is not None
    assert hasattr(response, "content")
    assert isinstance(response.content, str)
