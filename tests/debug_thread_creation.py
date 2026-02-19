"""Debug script to compare working vs non-working thread creation.

This helps identify what's different between the two approaches.
"""

from support_agent.config import get_settings
from support_agent.cortex_agent.rest_client import CortexAgentsRestClient


def test_with_test_app():
    """Test with 'test_app' origin (like check_cortex_availability)."""
    print("\n🔍 Test A: Create thread with origin='test_app'")
    print("-" * 60)

    try:
        settings = get_settings()
        client = CortexAgentsRestClient(
            account_url=settings.snowflake_account_url,
            token=settings.snowflake_rest_token,
        )
        thread_id = client.create_thread(origin_application="test_app")
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None
    else:
        print("✅ SUCCESS: Threads API available!")
        return thread_id


def test_with_settings_value():
    """Test with settings.cortex_origin_application (like demo)."""
    print("\n🔍 Test B: Create thread with settings.cortex_origin_application")
    print("-" * 60)

    try:
        settings = get_settings()
        print(
            f"   cortex_origin_application = '{settings.cortex_origin_application}'"
        )

        client = CortexAgentsRestClient(
            account_url=settings.snowflake_account_url,
            token=settings.snowflake_rest_token,
            origin_application=settings.cortex_origin_application,
        )
        thread_id = client.create_thread(
            origin_application=settings.cortex_origin_application
        )
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None
    else:
        print("✅ SUCCESS: Threads API available!")
        return thread_id


def test_with_settings_value_in_init_only():
    """Test with origin in __init__ but not in create_thread()."""
    print("\n🔍 Test C: Origin in __init__ only")
    print("-" * 60)

    try:
        settings = get_settings()
        print(
            f"   cortex_origin_application = '{settings.cortex_origin_application}'"
        )

        client = CortexAgentsRestClient(
            account_url=settings.snowflake_account_url,
            token=settings.snowflake_rest_token,
            origin_application=settings.cortex_origin_application,
        )
        # Don't pass origin_application parameter
        thread_id = client.create_thread()
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None
    else:
        print("✅ SUCCESS: Threads API available!")
        return thread_id


def test_with_settings_value_in_method_only():
    """Test with origin in create_thread() but not in __init__."""
    print("\n🔍 Test D: Origin in create_thread() only")
    print("-" * 60)

    try:
        settings = get_settings()
        print(
            f"   cortex_origin_application = '{settings.cortex_origin_application}'"
        )

        client = CortexAgentsRestClient(
            account_url=settings.snowflake_account_url,
            token=settings.snowflake_rest_token,
            # Don't pass origin_application to __init__
        )
        thread_id = client.create_thread(
            origin_application=settings.cortex_origin_application
        )
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return None
    else:
        print("✅ SUCCESS: thread_id = {thread_id}")
        return thread_id


def main():
    """Run all tests."""
    print("=" * 60)
    print("Thread Creation Debug Tests")
    print("=" * 60)

    results = {
        "test_app": test_with_test_app(),
        "settings_both": test_with_settings_value(),
        "settings_init_only": test_with_settings_value_in_init_only(),
        "settings_method_only": test_with_settings_value_in_method_only(),
    }

    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)

    for name, thread_id in results.items():
        status = "✅ WORKS" if thread_id else "❌ FAILS"
        print(f"{status}: {name}")

    # Clean up created threads
    if any(results.values()):
        print("\n🧹 Cleaning up test threads...")
        try:
            settings = get_settings()
            client = CortexAgentsRestClient(
                account_url=settings.snowflake_account_url,
                token=settings.snowflake_rest_token,
            )
            for thread_id in results.values():
                if thread_id:
                    try:
                        client.delete_thread(thread_id)
                        print(f"   Deleted thread {thread_id}")
                    except Exception as e:
                        print(f"   Failed to delete thread {thread_id}: {e}")
        except Exception as e:
            print(f"   Failed to clean up threads: {e}")


if __name__ == "__main__":
    main()
