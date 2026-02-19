"""Streamlit demo app.

Minimal chat UI for Snowflake Cortex Agents with persistent thread management.

State stored in `st.session_state`:
- `conversation_id`: Unique conversation identifier (persists thread state in DB)
- `chat_messages`: In-memory message history for UI display
- `conversations_cache`: Per-conversation message history {conv_id: [messages]}
- `use_threads`: Whether to use Threads API (falls back to stateless if unsupported)

Thread state (thread_id, parent_message_id) is managed in Snowflake database
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


def _new_conversation_id() -> str:
    import uuid

    return str(uuid.uuid4())[:8]


def _reset_chat_state() -> None:
    # Persist current messages before resetting
    _save_current_messages()
    st.session_state.chat_messages = []
    st.session_state.use_threads = True
    st.session_state.threads_notice_shown = False
    st.session_state.threads_unsupported_details = ""
    st.session_state.conversation_id = _new_conversation_id()


def _save_current_messages() -> None:
    """Persist the current chat_messages into the in-session cache."""
    conv_id = st.session_state.get("conversation_id")
    messages = st.session_state.get("chat_messages", [])
    if conv_id and messages:
        st.session_state.conversations_cache[conv_id] = list(messages)


def _switch_conversation(conv_id: str) -> None:
    """Switch to a different conversation, saving the current one first."""
    _save_current_messages()
    st.session_state.conversation_id = conv_id
    # Restore cached messages for the target conversation (may be empty)
    st.session_state.chat_messages = list(
        st.session_state.conversations_cache.get(conv_id, [])
    )
    st.session_state.use_threads = True
    st.session_state.threads_notice_shown = False
    st.session_state.threads_unsupported_details = ""


def _ensure_state_initialized() -> None:
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "conversations_cache" not in st.session_state:
        st.session_state.conversations_cache = {}
    if "use_threads" not in st.session_state:
        st.session_state.use_threads = True
    if "threads_notice_shown" not in st.session_state:
        st.session_state.threads_notice_shown = False
    if "threads_unsupported_details" not in st.session_state:
        st.session_state.threads_unsupported_details = ""
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = _new_conversation_id()


def _render_history_sidebar(session: object, settings: object) -> None:
    """Render the conversation history panel in the sidebar."""
    from support_agent.cortex_agent.conversation_manager import ConversationManager
    from support_agent.cortex_agent.service import get_cortex_rest_client

    with st.sidebar:
        st.header("Conversation History")

        if st.button("+ New chat", use_container_width=True, type="primary"):
            _reset_chat_state()
            st.rerun()

        st.divider()

        try:
            manager = ConversationManager(session=session, settings=settings)
            rest_client = get_cortex_rest_client(settings)
            conversations = manager.list_conversations(limit=30)
        except Exception as exc:
            st.warning(f"Could not load history: {exc}")
            conversations = []
            manager = None
            rest_client = None

        # Always include the current conversation even if it isn't in the DB yet
        current_id = st.session_state.conversation_id
        db_ids = {c["CONVERSATION_ID"] for c in conversations}
        if current_id not in db_ids and st.session_state.chat_messages:
            # Prepend a synthetic record for the in-progress conversation
            conversations = [
                {
                    "CONVERSATION_ID": current_id,
                    "UPDATED_AT": None,
                    "THREAD_ID": None,
                },
                *conversations,
            ]

        if not conversations:
            st.caption("No conversations yet.")
        else:
            for conv in conversations:
                conv_id = conv["CONVERSATION_ID"]
                updated_at = conv.get("UPDATED_AT")
                thread_id = conv.get("THREAD_ID")

                is_active = conv_id == current_id
                label = f"{'▶ ' if is_active else ''}{conv_id}"

                # Sub-caption line
                parts: list[str] = []
                if thread_id:
                    parts.append(f"thread {thread_id}")
                if updated_at:
                    try:
                        ts = str(updated_at)[:16]  # "YYYY-MM-DD HH:MM"
                        parts.append(ts)
                    except Exception as e:
                        print(f"Warning: Could not format timestamp: {e!s}")

                caption = " · ".join(parts) if parts else "in progress"

                btn_type = "primary" if is_active else "secondary"
                if (
                    st.button(
                        label,
                        key=f"conv_{conv_id}",
                        use_container_width=True,
                        type=btn_type,
                        help=caption,
                    )
                    and not is_active
                ):
                    _switch_conversation(conv_id)
                    # If the local cache has no messages for this conversation
                    # (e.g. it was started in a previous browser session), load
                    # them from the Cortex thread so the chat UI is populated.
                    if (
                        not st.session_state.chat_messages
                        and manager is not None
                        and rest_client is not None
                    ):
                        with st.spinner("Loading conversation history…"):
                            loaded = manager.load_conversation_messages(
                                conv_id, rest_client
                            )
                        if loaded:
                            st.session_state.chat_messages = loaded
                            st.session_state.conversations_cache[conv_id] = loaded
                    st.rerun()

                st.caption(f"  {caption}")


def main() -> None:
    """Run the Streamlit chat UI."""
    from support_agent.config import get_settings
    from support_agent.cortex_agent.rest_client import CortexAgentsRestClient
    from support_agent.cortex_agent.service import chat_with_conversation
    from support_agent.snowflake_client import create_snowpark_session

    st.set_page_config(page_title="Support Tickets Agent", layout="wide")
    st.title("Support Tickets Agent")

    _ensure_state_initialized()

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

    # Render the sidebar history panel
    _render_history_sidebar(session, settings)

    # Show conversation tracking info above the chat
    st.caption(
        f"Conversation: **{st.session_state.conversation_id}** · "
        f"{len(st.session_state.chat_messages) // 2} exchange(s)"
    )

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
                        "Threads API not available. Falling back to stateless mode (conversation history maintained in session only)."
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
    # Persist updated history so the sidebar reflects this conversation
    _save_current_messages()
    # Note: thread state is now persisted in database automatically by chat_with_conversation


if __name__ == "__main__":
    main()
