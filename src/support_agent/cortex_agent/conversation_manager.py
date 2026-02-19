"""Conversation management for Cortex Agent threads.

This module provides database-backed conversation state management,
ensuring thread continuity across sessions and proper parent message tracking.
"""

from __future__ import annotations

from snowflake.snowpark import Session

from support_agent.config import Settings
from support_agent.cortex_agent.rest_client import CortexAgentsRestClient


class ConversationManager:
    """Manages conversation-to-thread mapping with database persistence.

    This class solves the problem of thread continuity by:
    1. Storing thread_id and parent_message_id in Snowflake
    2. Reusing existing threads for the same conversation
    3. Tracking the latest message IDs for proper continuation
    """

    def __init__(self, session: Session, settings: Settings):
        """Initialize the conversation manager.

        Args:
            session: Snowpark session for database access
            settings: Application settings with database/schema config
        """
        self.session = session
        self.settings = settings
        self._conversations_table = (
            f"{settings.database}.APP.CORTEX_CONVERSATIONS"
        )

    def get_or_create_thread(
        self, conversation_id: str, rest_client: CortexAgentsRestClient
    ) -> tuple[int, int]:
        """Get existing thread or create a new one for a conversation.

        Args:
            conversation_id: Unique conversation identifier
            rest_client: CortexAgentsRestClient for creating new threads

        Returns:
            Tuple of (thread_id, parent_message_id):
            - thread_id: The thread ID to use
            - parent_message_id: 0 for first message, or last assistant message_id

        Note:
            This method checks the database first. If a thread exists, it reuses it.
            Otherwise, it creates a new thread and stores the mapping.
        """
        # Check if conversation already has a thread
        existing = self._get_thread_from_db(conversation_id)
        if existing:
            thread_id, parent_message_id = existing
            print(
                f"=> Reusing thread {thread_id} for conversation {conversation_id}"
            )
            return thread_id, parent_message_id

        # Create new thread
        thread_id = rest_client.create_thread(
            origin_application=self.settings.cortex_origin_application
        )
        print(
            f"=> Created new thread {thread_id} for conversation {conversation_id}"
        )

        # Store mapping in database
        self._store_conversation_mapping(
            conversation_id=conversation_id,
            thread_id=thread_id,
            last_assistant_message_id=None,  # No messages yet
        )

        return thread_id, 0  # parent_message_id=0 for first message

    def update_conversation(
        self,
        conversation_id: str,
        thread_id: int,
        assistant_message_id: int,
    ) -> None:
        """Update conversation state after receiving assistant response.

        Args:
            conversation_id: Unique conversation identifier
            thread_id: The thread ID used
            assistant_message_id: The message ID from the latest assistant response

        Note:
            Call this after each successful agent response to maintain proper
            parent_message_id tracking for the next turn.
        """
        self._store_conversation_mapping(
            conversation_id=conversation_id,
            thread_id=thread_id,
            last_assistant_message_id=assistant_message_id,
        )

    def _get_thread_from_db(
        self, conversation_id: str
    ) -> tuple[int, int] | None:
        """Retrieve thread info from database.

        Returns:
            Tuple of (thread_id, parent_message_id) or None if not found
        """
        try:
            result = self.session.sql(
                f"""
                SELECT THREAD_ID, LAST_ASSISTANT_MESSAGE_ID
                FROM {self._conversations_table}
                WHERE CONVERSATION_ID = ?
                """,  # noqa: S608
                params=[conversation_id],
            ).collect()

            if result and len(result) > 0:
                row = result[0]
                thread_id = int(row["THREAD_ID"])
                # If no assistant message yet, use 0
                parent_message_id = (
                    int(row["LAST_ASSISTANT_MESSAGE_ID"])
                    if row["LAST_ASSISTANT_MESSAGE_ID"] is not None
                    else 0
                )
                return thread_id, parent_message_id

        except Exception as e:
            print(f"Warning: Could not retrieve thread info: {e!s}")

        return None

    def _store_conversation_mapping(
        self,
        conversation_id: str,
        thread_id: int,
        last_assistant_message_id: int | None,
    ) -> None:
        """Store or update conversation-to-thread mapping.

        Uses MERGE to handle both insert and update cases.
        """
        try:
            # Use parameterized query for safety
            last_msg_id_expr = (
                "NULL"
                if last_assistant_message_id is None
                else str(last_assistant_message_id)
            )

            self.session.sql(
                f"""
                MERGE INTO {self._conversations_table} t
                USING (
                  SELECT
                    ? AS CONVERSATION_ID,
                    ? AS THREAD_ID,
                    {last_msg_id_expr} AS LAST_ASSISTANT_MESSAGE_ID,
                    ? AS ORIGIN_APPLICATION,
                    CURRENT_TIMESTAMP() AS UPDATED_AT
                ) s
                ON t.CONVERSATION_ID = s.CONVERSATION_ID
                WHEN MATCHED THEN UPDATE SET
                  THREAD_ID = s.THREAD_ID,
                  LAST_ASSISTANT_MESSAGE_ID = s.LAST_ASSISTANT_MESSAGE_ID,
                  ORIGIN_APPLICATION = s.ORIGIN_APPLICATION,
                  UPDATED_AT = s.UPDATED_AT
                WHEN NOT MATCHED THEN INSERT (
                  CONVERSATION_ID,
                  THREAD_ID,
                  LAST_ASSISTANT_MESSAGE_ID,
                  ORIGIN_APPLICATION,
                  CREATED_AT,
                  UPDATED_AT
                ) VALUES (
                  s.CONVERSATION_ID,
                  s.THREAD_ID,
                  s.LAST_ASSISTANT_MESSAGE_ID,
                  s.ORIGIN_APPLICATION,
                  CURRENT_TIMESTAMP(),
                  s.UPDATED_AT
                )
                """,  # noqa: S608
                params=[
                    conversation_id,
                    thread_id,
                    self.settings.cortex_origin_application,
                ],
            ).collect()

        except Exception as e:
            print(f"Warning: Could not store conversation mapping: {e!s}")

    def list_conversations(self, limit: int = 50) -> list[dict]:
        """List recent conversations with their thread info.

        Args:
            limit: Maximum number of conversations to return

        Returns:
            List of conversation records with thread metadata
        """
        try:
            result = self.session.sql(
                f"""
                SELECT
                    CONVERSATION_ID,
                    THREAD_ID,
                    LAST_ASSISTANT_MESSAGE_ID,
                    ORIGIN_APPLICATION,
                    CREATED_AT,
                    UPDATED_AT
                FROM {self._conversations_table}
                ORDER BY UPDATED_AT DESC
                LIMIT {limit}
                """  # noqa: S608
            ).collect()

            return [row.as_dict() for row in result]

        except Exception as e:
            print(f"Warning: Could not list conversations: {e!s}")
            return []

    def load_conversation_messages(
        self,
        conversation_id: str,
        rest_client: CortexAgentsRestClient,
        *,
        page_size: int = 100,
    ) -> list[dict]:
        """Load message history for a conversation from its Cortex thread.

        Fetches all messages stored in the Cortex thread and converts them
        into simple ``{"role": ..., "content": ...}`` dicts suitable for
        rendering in the Streamlit chat UI.

        Args:
            conversation_id: The conversation whose history to load.
            rest_client: CortexAgentsRestClient for the Threads API.
            page_size: How many messages to retrieve per page.

        Returns:
            Ordered list of ``{"role": str, "content": str}`` dicts.
            Returns an empty list when the conversation has no thread yet or
            when the API call fails.
        """
        import json

        existing = self._get_thread_from_db(conversation_id)
        if not existing:
            return []

        thread_id, _ = existing
        try:
            describe = rest_client.describe_thread(
                thread_id, page_size=page_size
            )
        except Exception as e:
            print(
                f"Warning: Could not describe thread {thread_id}: {e!s}"
            )
            return []

        messages: list[dict] = []
        for msg in describe.messages:
            role = msg.role  # "user" or "assistant"
            if role not in ("user", "assistant"):
                continue

            # message_payload is a JSON string encoding the Cortex message
            # object, e.g. {"role":"user","content":[{"type":"text","text":"..."}]}
            text = ""
            try:
                payload = json.loads(msg.message_payload)
                content = payload.get("content") or []
                parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        t = item.get("text")
                        if isinstance(t, str) and t:
                            parts.append(t)
                text = "\n".join(parts).strip()
            except Exception:
                # Fallback: treat payload as plain text
                text = msg.message_payload.strip()

            if text:
                messages.append({"role": role, "content": text})

        return messages
