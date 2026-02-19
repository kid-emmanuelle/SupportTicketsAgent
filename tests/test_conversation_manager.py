"""Tests for ConversationManager with database persistence."""

from unittest.mock import Mock

from support_agent.config import Settings
from support_agent.cortex_agent.conversation_manager import ConversationManager


def test_conversation_manager_creates_new_thread():
    """Test that ConversationManager creates a new thread for new conversations."""
    # Mock session
    session = Mock()
    session.sql.return_value.collect.return_value = []  # No existing thread

    # Mock settings
    settings = Settings(
        database="TEST_DB",
        cortex_origin_application="test_app",
        account="test_account",
        user="test_user",
        password="test_pass",  # noqa: S106
    )

    # Mock REST client
    rest_client = Mock()
    rest_client.create_thread.return_value = 12345

    manager = ConversationManager(session, settings)

    # Create thread for new conversation
    thread_id, parent_message_id = manager.get_or_create_thread(
        conversation_id="test_conv_001",
        rest_client=rest_client,
    )

    assert thread_id == 12345
    assert parent_message_id == 0
    rest_client.create_thread.assert_called_once()


def test_conversation_manager_reuses_existing_thread():
    """Test that ConversationManager reuses existing thread for same conversation."""
    # Mock session - return existing thread
    session = Mock()
    mock_row = Mock()
    mock_row.__getitem__ = lambda _, key: {
        "THREAD_ID": 99999,
        "LAST_ASSISTANT_MESSAGE_ID": 42,
    }[key]
    session.sql.return_value.collect.return_value = [mock_row]

    settings = Settings(
        database="TEST_DB",
        cortex_origin_application="test_app",
        account="test_account",
        user="test_user",
        password="test_pass",  # noqa: S106
    )

    rest_client = Mock()

    manager = ConversationManager(session, settings)

    # Get existing thread
    thread_id, parent_message_id = manager.get_or_create_thread(
        conversation_id="test_conv_001",
        rest_client=rest_client,
    )

    assert thread_id == 99999
    assert parent_message_id == 42
    # Should NOT create new thread
    rest_client.create_thread.assert_not_called()


def test_conversation_manager_update_conversation():
    """Test that update_conversation stores assistant message ID."""
    session = Mock()
    session.sql.return_value.collect.return_value = []

    settings = Settings(
        database="TEST_DB",
        cortex_origin_application="test_app",
        account="test_account",
        user="test_user",
        password="test_pass",  # noqa: S106
    )

    manager = ConversationManager(session, settings)

    # Update conversation with new message
    manager.update_conversation(
        conversation_id="test_conv_001",
        thread_id=12345,
        assistant_message_id=999,
    )

    # Verify SQL was called
    session.sql.assert_called()
    call_args = session.sql.call_args[0][0]
    assert "MERGE INTO" in call_args
    assert "CORTEX_CONVERSATIONS" in call_args
