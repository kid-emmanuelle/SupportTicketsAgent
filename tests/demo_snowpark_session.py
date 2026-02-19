import json

import requests
import snowflake.connector


# --- CONFIGURATION ---
conn_params = {
    "user": "EMMA",
    "password": "xsfLMb$xjQ$EA&i@8hdAn$3BHQ!",
    "account": "JKIALNL-UB53586",
    "warehouse": "COMPUTE_WH",
    "role": "ACCOUNTADMIN",
}

# Use a hardcoded ID for testing "Persistence"
# In a real app, this would come from a cookie or Login ID
TEST_SESSION_ID = "KID_SESSION_001"


def get_session_from_snowflake(conn, session_id):
    cursor = conn.cursor()
    # Fully qualifying the name ensures it never gets lost
    query = "SELECT CHAT_HISTORY FROM PROJECT_DB.APP.CORTEX_CHAT_SESSIONS WHERE SESSION_ID = %s"
    cursor.execute(query, (session_id,))
    result = cursor.fetchone()
    return json.loads(result[0]) if result else None


def save_session_to_snowflake(conn, session_id, history):
    cursor = conn.cursor()
    history_json = json.dumps(history)
    # Fully qualifying here too
    query = """
        MERGE INTO PROJECT_DB.APP.CORTEX_CHAT_SESSIONS AS target
        USING (SELECT %s AS id, PARSE_JSON(%s) AS hist) AS source
        ON target.SESSION_ID = source.id
        WHEN MATCHED THEN UPDATE SET CHAT_HISTORY = source.hist, LAST_UPDATED = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN INSERT (SESSION_ID, CHAT_HISTORY) VALUES (source.id, source.hist)
    """
    cursor.execute(query, (session_id, history_json))
    conn.commit()


def test_persistent_chat():
    conn = snowflake.connector.connect(**conn_params)

    # --- ADD THIS PART ---
    cursor = conn.cursor()
    cursor.execute("USE DATABASE PROJECT_DB")
    cursor.execute("USE SCHEMA APP")
    # ---------------------

    # 1. Load History (The Persistence Check)
    print(f"Checking for session: {TEST_SESSION_ID}...")
    thread_history = get_session_from_snowflake(conn, TEST_SESSION_ID)

    if not thread_history:
        print("No previous session found. Initializing new chat...")
        thread_history = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "You are a helpful IT assistant."}
                ],
            }
        ]
    else:
        print(
            f"Success! Resumed session with {len(thread_history)} previous messages."
        )

    # 2. Add a new test message
    user_msg = "Remember this code: 998877"
    thread_history.append(
        {"role": "user", "content": [{"type": "text", "text": user_msg}]}
    )

    # 3. Call Cortex API (Simplified REST call)
    host = conn.account + ".snowflakecomputing.com"
    url = f"https://{host}/api/v2/cortex/agent:run"
    headers = {
        "Authorization": f'Snowflake Token="{conn.rest.token}"',
        "Content-Type": "application/json",
    }

    payload = {"model": "llama3.1-70b", "messages": thread_history}
    response = requests.post(url, headers=headers, json=payload, timeout=30)

    if response.status_code == 200:
        # Note: Parsing logic for non-streaming for simplicity in this test
        print("Agent responded successfully.")
        # (Usually you would parse the stream here as we did before)

        # 4. Save back to Snowflake
        save_session_to_snowflake(conn, TEST_SESSION_ID, thread_history)
        print("Session state saved to Snowflake Table.")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    test_persistent_chat()
