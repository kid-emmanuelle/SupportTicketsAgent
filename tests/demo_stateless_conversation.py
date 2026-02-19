"""Demo script showing stateless conversation management (without Threads API).

This script demonstrates conversation management when Threads API is not available.
Instead of using threads, it maintains conversation history in the messages array.

Usage:
    python tests/demo_stateless_conversation.py
"""

from support_agent.config import get_settings
from support_agent.cortex_agent.rest_client import CortexAgentsRestClient


def main():
    """Run a stateless conversation demo."""
    print("=" * 60)
    print("Cortex Agent - Stateless Conversation Demo")
    print("(No Threads API required)")
    print("=" * 60)

    # Initialize
    settings = get_settings()

    if not settings.snowflake_account_url or not settings.snowflake_rest_token:
        print("\n❌ Error: Missing REST configuration.")
        print("Set SNOWFLAKE_ACCOUNT_URL and SNOWFLAKE_REST_TOKEN in .env")
        return

    client = CortexAgentsRestClient(
        account_url=settings.snowflake_account_url,
        token=settings.snowflake_rest_token,
        origin_application=settings.cortex_origin_application,
    )

    # Conversation history (maintained in memory)
    conversation_history = []

    print("\n📝 Starting stateless conversation...")
    print("=" * 60)

    # Message 1
    user_msg_1 = "How do I reset my password?"
    print(f"\n👤 User: {user_msg_1}")

    conversation_history.append(
        {"role": "user", "content": [{"type": "text", "text": user_msg_1}]}
    )

    try:
        result1 = client.run_agent_with_object_messages(
            database=settings.database,
            schema=settings.cortex_agent_schema,
            agent_name=settings.cortex_agent_name,
            messages=conversation_history,
            stream=False,
        )

        print(f"\n🤖 Assistant: {result1.assistant_text[:200]}...")

        # Add assistant response to history
        conversation_history.append(
            {
                "role": "assistant",
                "content": [{"type": "text", "text": result1.assistant_text}],
            }
        )

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return

    # Message 2
    print("\n" + "=" * 60)
    user_msg_2 = "What if I don't receive the reset email?"
    print(f"\n👤 User: {user_msg_2}")

    conversation_history.append(
        {"role": "user", "content": [{"type": "text", "text": user_msg_2}]}
    )

    try:
        result2 = client.run_agent_with_object_messages(
            database=settings.database,
            schema=settings.cortex_agent_schema,
            agent_name=settings.cortex_agent_name,
            messages=conversation_history,
            stream=False,
        )

        print(f"\n🤖 Assistant: {result2.assistant_text[:200]}...")

        conversation_history.append(
            {
                "role": "assistant",
                "content": [{"type": "text", "text": result2.assistant_text}],
            }
        )

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return

    # Message 3 - test context retention
    print("\n" + "=" * 60)
    user_msg_3 = "Can you summarize what we discussed?"
    print(f"\n👤 User: {user_msg_3}")

    conversation_history.append(
        {"role": "user", "content": [{"type": "text", "text": user_msg_3}]}
    )

    try:
        result3 = client.run_agent_with_object_messages(
            database=settings.database,
            schema=settings.cortex_agent_schema,
            agent_name=settings.cortex_agent_name,
            messages=conversation_history,
            stream=False,
        )

        print(f"\n🤖 Assistant: {result3.assistant_text}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return

    print("\n" + "=" * 60)
    print("✅ Demo Complete!")
    print("=" * 60)
    print(f"\nTotal conversation length: {len(conversation_history)} messages")
    print("\n💡 Note: This stateless approach works without Threads API,")
    print("   but requires sending full conversation history with each call.")
    print("   It's a good fallback until Threads API is enabled.")


if __name__ == "__main__":
    main()
