"""Quick test to find valid origin_application formats."""

from support_agent.config import get_settings
from support_agent.cortex_agent.rest_client import CortexAgentsRestClient


def test_origin_format(origin_name: str) -> bool:
    """Test if an origin_application format is accepted."""
    try:
        settings = get_settings()
        client = CortexAgentsRestClient(
            account_url=settings.snowflake_account_url,
            token=settings.snowflake_rest_token,
        )
        thread_id = client.create_thread(origin_application=origin_name)
        print(f"✅ WORKS: '{origin_name}' -> thread {thread_id}")
        # Clean up
        try:
            client.delete_thread(thread_id)
        except Exception as e:
            print(f"   ⚠️ Failed to clean up thread {thread_id}: {e}")
    except Exception as e:
        if "390400" in str(e):
            print(f"❌ FAILS: '{origin_name}' (390400 error)")
        else:
            print(f"❌ FAILS: '{origin_name}' - {e}")
        return False
    else:
        print(f"✅ WORKS: '{origin_name}' -> thread {thread_id}")
        return True


def main():
    """Test various origin_application formats."""
    print("=" * 60)
    print("Testing origin_application format restrictions")
    print("=" * 60)

    test_cases = [
        "testapp",  # no separators
        "test_app",  # underscore (we know this works)
        "test-app",  # hyphen
        "test.app",  # dot
        "TestApp",  # camelCase
        "test app",  # space
        "support_tickets_agent",  # current value (fails)
        "support-tickets-agent",  # hyphen version
        "supportticketsagent",  # no separators
        "SupportTicketsAgent",  # CamelCase
    ]

    print()
    results = {}
    for test_case in test_cases:
        results[test_case] = test_origin_format(test_case)

    print("\n" + "=" * 60)
    print("📊 Valid formats:")
    print("=" * 60)
    for name, worked in results.items():
        if worked:
            print(f"  ✅ {name}")

    print("\n❌ Invalid formats:")
    for name, worked in results.items():
        if not worked:
            print(f"  ❌ {name}")


if __name__ == "__main__":
    main()
