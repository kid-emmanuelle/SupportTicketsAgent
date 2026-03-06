"""Service layer for Cortex Agent integrations.

This module keeps the legacy Snowpark/table-function call for simple usage and
adds thread-based conversation helpers using the Cortex Agents REST APIs.
"""

from __future__ import annotations

from snowflake.snowpark import Session

from ..config import Settings
from .client import call_cortex_agent
from .conversation_manager import ConversationManager
from .rest_client import (
    AgentRunResult,
    CortexAgentsRestClient,
)


def run_cortex_fallback(
    session: Session,
    settings: Settings,
    issue_description: str,
) -> dict:
    """Executes Cortex Agent as fallback when LangGraph fails. Returns standardized TicketState-compatible output."""
    response = call_cortex_agent(
        session=session,
        database=settings.database,
        schema=settings.cortex_agent_schema,
        agent_name=settings.cortex_agent_name,
        user_message=issue_description,
    )

    return {
        "final_response": response,
        "priority_level": "UNKNOWN",
        "topic": "fallback",
        "intent": "fallback",
        "retrieved_context": [],
    }


def get_cortex_rest_client(settings: Settings) -> CortexAgentsRestClient:
    """Create a CortexAgentsRestClient from Settings.

    Raises:
        ValueError: If required REST settings are not configured.
    """
    return CortexAgentsRestClient(
        account_url=settings.snowflake_account_url or settings.account,
        token=settings.snowflake_rest_token,
        origin_application=settings.cortex_origin_application,
    )


def start_thread(settings: Settings) -> int:
    """Create and return a new Cortex thread ID."""
    client = get_cortex_rest_client(settings)
    return client.create_thread(
        origin_application=settings.cortex_origin_application
    )


def chat_in_thread(
    settings: Settings,
    *,
    thread_id: int,
    parent_message_id: int,
    user_text: str,
    stream: bool = True,
) -> AgentRunResult:
    """Send a user message to an agent using a thread.

    Args:
        settings: Application settings.
        thread_id: The thread ID.
        parent_message_id: 0 for the first message; otherwise the last assistant message id.
        user_text: The user message content.
        stream: If true, uses SSE streaming to capture message IDs.

    Returns:
        AgentRunResult containing assistant text plus (if streaming) message IDs.
    """
    client = get_cortex_rest_client(settings)
    return client.run_agent_with_object(
        database=settings.database,
        schema=settings.cortex_agent_schema,
        agent_name=settings.cortex_agent_name,
        thread_id=thread_id,
        parent_message_id=parent_message_id,
        user_text=user_text,
        stream=stream,
    )


def chat_with_conversation(
    session: Session,
    settings: Settings,
    *,
    conversation_id: str,
    user_text: str,
    stream: bool = True,
) -> AgentRunResult:
    """Send a user message using conversation-based thread management.

    This function automatically:
    1. Retrieves or creates a thread for the conversation
    2. Tracks parent_message_id from database
    3. Updates conversation state after the response

    Args:
        session: Snowpark session for database access
        settings: Application settings
        conversation_id: Unique conversation identifier (e.g., session ID, user ID)
        user_text: The user message content
        stream: If true, uses SSE streaming to capture message IDs

    Returns:
        AgentRunResult containing assistant text and message IDs

    Example:
        >>> result = chat_with_conversation(
        ...     session=session,
        ...     settings=settings,
        ...     conversation_id="session_abc123",
        ...     user_text="How do I reset my password?"
        ... )
        >>> print(result.assistant_text)
    """
    manager = ConversationManager(session, settings)
    rest_client = get_cortex_rest_client(settings)

    # Get or create thread with proper parent_message_id
    thread_id, parent_message_id = manager.get_or_create_thread(
        conversation_id=conversation_id,
        rest_client=rest_client,
    )

    # Send message
    result = rest_client.run_agent_with_object(
        database=settings.database,
        schema=settings.cortex_agent_schema,
        agent_name=settings.cortex_agent_name,
        thread_id=thread_id,
        parent_message_id=parent_message_id,
        user_text=user_text,
        stream=stream,
    )

    # Update conversation state if we got an assistant message ID
    if result.assistant_message_id is not None:
        manager.update_conversation(
            conversation_id=conversation_id,
            thread_id=thread_id,
            assistant_message_id=result.assistant_message_id,
        )

    return result


def get_conversation_manager(
    session: Session, settings: Settings
) -> ConversationManager:
    """Create a ConversationManager instance.

    Args:
        session: Snowpark session for database access
        settings: Application settings

    Returns:
        ConversationManager instance for manual conversation management
    """
    return ConversationManager(session, settings)
