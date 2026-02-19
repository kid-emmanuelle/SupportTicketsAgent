"""Demo script showing conversation-based thread management.

This script demonstrates how to use the new ConversationManager to maintain
thread continuity across multiple interactions.

Usage:
    python tests/demo_conversation_manager.py
"""

from support_agent.config import get_settings
from support_agent.cortex_agent.service import chat_with_conversation
from support_agent.snowflake_client import create_snowpark_session


def main():
    """Run a simple conversation demo."""
    print("=" * 60)
    print("Cortex Agent - Conversation Manager Demo")
    print("=" * 60)

    # Initialize
    settings = get_settings()
    session = create_snowpark_session(settings)

    # Generate a conversation ID (in real app, this could be session ID, user ID, etc.)
    import uuid

    conversation_id = f"demo_{uuid.uuid4().hex[:8]}"

    print(f"\n📝 Conversation ID: {conversation_id}")
    print("\nThis demo shows how threads are automatically managed:\n")

    # First message - creates a new thread
    print("=" * 60)
    print("Message 1: How do I reset my password?")
    print("=" * 60)

    result1 = chat_with_conversation(
        session=session,
        settings=settings,
        conversation_id=conversation_id,
        user_text="How do I reset my password?",
        stream=True,
    )

    print(f"\n🤖 Assistant: {result1.assistant_text[:200]}...")
    if result1.user_message_id:
        print(f"   User Message ID: {result1.user_message_id}")
    if result1.assistant_message_id:
        print(f"   Assistant Message ID: {result1.assistant_message_id}")

    # Second message - reuses the same thread
    print("\n" + "=" * 60)
    print("Message 2: What if I don't receive the reset email?")
    print("=" * 60)

    result2 = chat_with_conversation(
        session=session,
        settings=settings,
        conversation_id=conversation_id,
        user_text="What if I don't receive the reset email?",
        stream=True,
    )

    print(f"\n🤖 Assistant: {result2.assistant_text[:200]}...")
    if result2.user_message_id:
        print(f"   User Message ID: {result2.user_message_id}")
    if result2.assistant_message_id:
        print(f"   Assistant Message ID: {result2.assistant_message_id}")

    print("\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("=" * 60)
    print(f"\nConversation '{conversation_id}' is now stored in the database.")
    print("If you run this again with the same conversation_id,")
    print("it will continue the existing thread!")

    session.close()


if __name__ == "__main__":
    main()
