"""Streamlit demo app.

Minimal chat UI for Snowflake Cortex Agents with persistent thread management.

State stored in `st.session_state`:
- `conversation_id`: Unique conversation identifier (persists thread state in DB)
- `chat_messages`: In-memory message history for UI display
- `use_threads`: Whether to use Threads API (falls back to stateless if unsupported)

Thread state (thread_id, parent_message_id) is now managed in Snowflake database
via ConversationManager, ensuring continuity across sessions.
"""

from __future__ import annotations

from pathlib import Path
import sys

import streamlit as st


# When running `streamlit run app/streamlit_app.py`, the repo's `src/` directory
# isn't guaranteed to be on `sys.path`. Add it so `support_agent` imports work.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_DIR = _REPO_ROOT / "src"
if _SRC_DIR.is_dir():
    src_dir_str = str(_SRC_DIR)
    if src_dir_str not in sys.path:
        sys.path.insert(0, src_dir_str)


def _reset_chat_state() -> None:
    st.session_state.chat_messages = []
    st.session_state.use_threads = True
    st.session_state.threads_notice_shown = False
    st.session_state.threads_unsupported_details = ""
    # Generate a new conversation session ID for tracking
    import uuid

    st.session_state.conversation_id = str(uuid.uuid4())[:8]


def _ensure_state_initialized() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "use_threads" not in st.session_state:
        st.session_state.use_threads = True
    if "threads_notice_shown" not in st.session_state:
        st.session_state.threads_notice_shown = False
    if "threads_unsupported_details" not in st.session_state:
        st.session_state.threads_unsupported_details = ""
    if "conversation_id" not in st.session_state:
        import uuid

        st.session_state.conversation_id = str(uuid.uuid4())[:8]


def main() -> None:
    """Run the Streamlit chat UI."""
    from support_agent.config import get_settings
    from support_agent.cortex_agent.rest_client import CortexAgentsRestClient
    from support_agent.cortex_agent.service import chat_with_conversation
    from support_agent.snowflake_client import create_snowpark_session

    st.set_page_config(page_title="Support Tickets Agent", layout="centered")
    st.title("Support Tickets Agent")

    _ensure_state_initialized()

    # Show conversation tracking info
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.caption(
            f"💬 Conversation: {st.session_state.conversation_id} | Messages: {len(st.session_state.chat_messages) // 2}"
        )
    with col_right:
        if st.button("New chat", use_container_width=True):
            _reset_chat_state()
            st.rerun()

    try:
        settings = get_settings()
        session = create_snowpark_session(settings)
    except Exception as exc:  # pragma: no cover
        st.error(f"Failed to load settings or create session: {exc}")
        st.stop()

    if not settings.snowflake_account_url or not settings.snowflake_rest_token:
        st.error(
            "Missing REST configuration. Set `SNOWFLAKE_ACCOUNT_URL` and `SNOWFLAKE_REST_TOKEN` in your environment."
        )
        st.stop()

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_text = st.chat_input("Ask about a support ticket…")
    if not user_text:
        return

    st.session_state.chat_messages.append(
        {"role": "user", "content": user_text}
    )
    with st.chat_message("user"):
        st.markdown(user_text)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                if st.session_state.use_threads:
                    # Use conversation-aware function with automatic persistence
                    result = chat_with_conversation(
                        session=session,
                        settings=settings,
                        conversation_id=st.session_state.conversation_id,
                        user_text=user_text,
                        stream=True,
                    )
                else:
                    # Fallback: stateless mode with full message history
                    client = CortexAgentsRestClient(
                        account_url=settings.snowflake_account_url,
                        token=settings.snowflake_rest_token,
                        origin_application=settings.cortex_origin_application,
                    )
                    messages = [
                        {
                            "role": m["role"],
                            "content": [{"type": "text", "text": m["content"]}],
                        }
                        for m in st.session_state.chat_messages
                    ]
                    result = client.run_agent_with_object_messages(
                        database=settings.database,
                        schema=settings.cortex_agent_schema,
                        agent_name=settings.cortex_agent_name,
                        messages=messages,
                        stream=False,
                    )
            except Exception as exc:
                msg = str(exc)
                if "390400" in msg and "operation not supported" in msg.lower():
                    st.session_state.use_threads = False
                    st.session_state.threads_unsupported_details = msg
                    st.info(
                        "⚠️ Threads API not available. Falling back to stateless mode (conversation history maintained in session only)."
                    )
                    st.rerun()  # Retry with stateless mode
                else:
                    st.error(f"Agent call failed: {exc}")
                    st.stop()

        assistant_text = result.assistant_text.strip() or "(No text returned.)"
        st.markdown(assistant_text)

    st.session_state.chat_messages.append(
        {"role": "assistant", "content": assistant_text}
    )
    # Note: thread state is now persisted in database automatically by chat_with_conversation


if __name__ == "__main__":
    main()
