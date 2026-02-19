"""Diagnose Cortex API availability in your Snowflake account.

This script checks which Cortex features are available and helps debug
the "390400: operation not supported" error.

Usage:
    python tests/check_cortex_availability.py
"""

from support_agent.config import get_settings
from support_agent.cortex_agent.rest_client import CortexAgentsRestClient


def test_basic_agent_call():
    """Test if agent:run works without threads."""
    print("\n🔍 Test 1: Basic Agent Call (no threads)")
    print("-" * 60)

    try:
        settings = get_settings()
        client = CortexAgentsRestClient(
            account_url=settings.snowflake_account_url,
            token=settings.snowflake_rest_token,
        )

        result = client.run_agent_with_object_messages(
            database=settings.database,
            schema=settings.cortex_agent_schema,
            agent_name=settings.cortex_agent_name,
            messages=[
                {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
            ],
            stream=False,
        )

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False
    else:
        print("✅ SUCCESS: Basic agent calls work!")
        print(f"   Response: {result.assistant_text[:100]}...")
        return True


def test_thread_creation():
    """Test if Threads API is available."""
    print("\n🔍 Test 2: Create Thread (Threads API)")
    print("-" * 60)

    try:
        settings = get_settings()
        client = CortexAgentsRestClient(
            account_url=settings.snowflake_account_url,
            token=settings.snowflake_rest_token,
        )

        thread_id = client.create_thread(origin_application="test_app")
        print("✅ SUCCESS: Threads API available!")
        print(f"   Created thread: {thread_id}")

        # Clean up - try to delete the test thread
        try:
            client.delete_thread(thread_id)
            print(f"   Cleaned up test thread: {thread_id}")
        except Exception as e:
            print(f"   Failed to clean up test thread {thread_id}: {e}")

    except Exception as e:
        error_msg = str(e)
        if (
            "390400" in error_msg
            or "operation not supported" in error_msg.lower()
        ):
            print("❌ FAILED: Threads API not enabled")
            print("   Error: 390400 - operation not supported")
            print("\n   📋 Action Required:")
            print("   1. Check if your region supports Threads API")
            print("   2. Verify you have Enterprise Edition")
            print("   3. Contact Snowflake support to enable Threads API")
            print("\n   📖 See docs/ENABLE_THREADS_API.md for details")
        else:
            print(f"❌ FAILED: {e}")
        return False
    else:
        print("✅ SUCCESS: Threads API available!")
        return True


def test_thread_list():
    """Test if we can list threads."""
    print("\n🔍 Test 3: List Threads")
    print("-" * 60)

    try:
        settings = get_settings()
        client = CortexAgentsRestClient(
            account_url=settings.snowflake_account_url,
            token=settings.snowflake_rest_token,
        )

        threads = client.list_threads()
    except Exception as e:
        error_msg = str(e)
        if "390400" in error_msg:
            print("❌ FAILED: Threads API not enabled")
        else:
            print(f"❌ FAILED: {e}")
        return False
    else:
        print("✅ SUCCESS: Can list threads")
        print(f"   Found {len(threads)} thread(s)")
        return True


def main():
    """Run diagnostic tests."""
    print("=" * 60)
    print("Cortex API Availability Diagnostic")
    print("=" * 60)

    try:
        settings = get_settings()
        print("\n📋 Configuration:")
        print(f"   Account URL: {settings.snowflake_account_url}")
        print(f"   Database: {settings.database}")
        print(f"   Schema: {settings.cortex_agent_schema}")
        print(f"   Agent: {settings.cortex_agent_name}")
        print(
            f"   Token: {'✓ Set' if settings.snowflake_rest_token else '✗ Missing'}"
        )
    except Exception as e:
        print(f"\n❌ Configuration Error: {e}")
        return

    # Run tests
    results = {
        "basic_agent": test_basic_agent_call(),
        "thread_creation": test_thread_creation(),
        "thread_list": test_thread_list(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)

    if results["basic_agent"]:
        print("\n✅ Agent calls: Working")
        print(
            "   → You can use stateless mode (run demo_stateless_conversation.py)"
        )
    else:
        print("\n❌ Agent calls: Not working")
        print("   → Check agent configuration and credentials")

    if results["thread_creation"] or results["thread_list"]:
        print("\n✅ Threads API: Available")
        print(
            "   → You can use threaded conversations (run demo_conversation_manager.py)"
        )
    else:
        print("\n❌ Threads API: Not available")
        print("   → Use stateless mode or request Threads API access")
        print("   → See docs/ENABLE_THREADS_API.md for instructions")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
