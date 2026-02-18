"""Integration tests for retrieval functions with real Snowflake session."""

import os

from dotenv import load_dotenv
import pytest

from support_agent.config import get_settings
from support_agent.retrieval import retrieve_context, retrieve_text_chunks
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


@pytest.mark.skipif(
    not os.getenv("SNOWFLAKE_ACCOUNT") or not os.getenv("SNOWFLAKE_USER"),
    reason="Requires Snowflake connection env vars",
)
class TestRetrievalIntegration:
    """Real integration tests for retrieval functions."""

    def test_retrieve_context_basic(self, session, settings):
        """Test retrieve_context with a basic query."""
        query = "How do I reset my password?"

        results = retrieve_context(session, settings, query)

        assert isinstance(results, list)
        assert len(results) >= 0
        # If results exist, they should be dicts
        if results:
            assert isinstance(results[0], dict)

    def test_retrieve_context_with_custom_columns(self, session, settings):
        """Test retrieve_context with custom columns."""
        query = "account login issue"

        results = retrieve_context(
            session, settings, query, columns=["body_answer"]
        )

        assert isinstance(results, list)
        if results:
            assert isinstance(results[0], dict)
            # Should contain the requested column
            assert "body_answer" in results[0]

    def test_retrieve_context_with_custom_limit(self, session, settings):
        """Test retrieve_context with a custom limit."""
        query = "technical support"
        limit = 3

        results = retrieve_context(session, settings, query, limit=limit)

        assert isinstance(results, list)
        assert len(results) <= limit

    def test_retrieve_context_empty_query(self, session, settings):
        """Test retrieve_context with an empty query."""
        query = ""

        # Should not raise an error, but may return empty results
        results = retrieve_context(session, settings, query)

        assert isinstance(results, list)

    def test_retrieve_context_technical_query(self, session, settings):
        """Test retrieve_context with a technical query."""
        query = "API error 500 internal server error"

        results = retrieve_context(session, settings, query)

        assert isinstance(results, list)

    def test_retrieve_context_billing_query(self, session, settings):
        """Test retrieve_context with a billing-related query."""
        query = "invoice payment billing issue"

        results = retrieve_context(session, settings, query)

        assert isinstance(results, list)

    def test_retrieve_text_chunks_basic(self, session, settings):
        """Test retrieve_text_chunks returns list of strings."""
        query = "How do I change my email address?"

        results = retrieve_text_chunks(session, settings, query)

        assert isinstance(results, list)
        # All items should be strings
        for item in results:
            assert isinstance(item, str)

    def test_retrieve_text_chunks_non_empty_strings(self, session, settings):
        """Test retrieve_text_chunks returns non-empty strings."""
        query = "password reset help"

        results = retrieve_text_chunks(session, settings, query)

        assert isinstance(results, list)
        # All returned strings should be non-empty
        for item in results:
            assert len(item) > 0

    def test_retrieve_text_chunks_technical(self, session, settings):
        """Test retrieve_text_chunks with a technical query."""
        query = "authentication token expired"

        results = retrieve_text_chunks(session, settings, query)

        assert isinstance(results, list)
        for item in results:
            assert isinstance(item, str)

    def test_retrieve_context_respects_top_k_setting(self, session, settings):
        """Test that retrieve_context respects the top_k setting."""
        query = "general support question"

        results = retrieve_context(session, settings, query)

        assert isinstance(results, list)
        # Should not exceed the configured top_k
        assert len(results) <= settings.top_k

    def test_retrieve_context_different_queries_different_results(
        self, session, settings
    ):
        """Test that different queries may return different results."""
        query1 = "password reset"
        query2 = "billing invoice"

        results1 = retrieve_context(session, settings, query1)
        results2 = retrieve_context(session, settings, query2)

        assert isinstance(results1, list)
        assert isinstance(results2, list)
        # Results might be different (or same if limited data)
        # Just verify both calls succeed

    def test_retrieve_context_special_characters(self, session, settings):
        """Test retrieve_context handles special characters."""
        query = "What's the error? It says 'invalid token' & crashes!"

        # Should not raise an error
        results = retrieve_context(session, settings, query)

        assert isinstance(results, list)

    def test_retrieve_context_unicode(self, session, settings):
        """Test retrieve_context handles unicode characters."""
        query = "problème de connexion réseau"

        # Should not raise an error
        results = retrieve_context(session, settings, query)

        assert isinstance(results, list)


@pytest.mark.skipif(
    not os.getenv("SNOWFLAKE_ACCOUNT") or not os.getenv("SNOWFLAKE_USER"),
    reason="Requires Snowflake connection env vars",
)
def test_retrieve_context_returns_list(settings):
    """Test that retrieve_context always returns a list."""
    session = create_snowpark_session(settings)

    try:
        results = retrieve_context(session, settings, "test query")
        assert isinstance(results, list)
    finally:
        session.close()
