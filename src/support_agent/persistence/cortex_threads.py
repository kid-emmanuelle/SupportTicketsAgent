"""Persist Cortex thread history to Snowflake tables.

These helpers are optional and intended for later UI work (e.g. Streamlit).
They cache thread/message snapshots locally in your Snowflake database.

Tables are created by sql/45_cortex_threads_history.sql.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from snowflake.snowpark import Session

from support_agent.config import Settings
from support_agent.cortex_agent.rest_client import ThreadDescribe


def _ts_from_ms(ms: int | None) -> datetime | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=UTC).replace(tzinfo=None)


def cache_thread_describe(
    session: Session, settings: Settings, describe: ThreadDescribe
) -> None:
    """Cache a ThreadDescribe (metadata + messages) into Snowflake."""
    threads_table = f"{settings.database}.APP.CORTEX_THREADS"
    messages_table = f"{settings.database}.APP.CORTEX_THREAD_MESSAGES"

    now = datetime.now(UTC).replace(tzinfo=None)
    md = describe.metadata
    md_row: dict[str, Any] = {
        "THREAD_ID": md.thread_id,
        "THREAD_NAME": md.thread_name,
        "ORIGIN_APPLICATION": md.origin_application,
        "CREATED_ON": _ts_from_ms(md.created_on_ms),
        "UPDATED_ON": _ts_from_ms(md.updated_on_ms),
        "INGESTED_AT": now,
    }

    session.create_dataframe([md_row]).write.mode("append").save_as_table(
        threads_table
    )

    msg_rows: list[dict[str, Any]] = []
    for m in describe.messages:
        msg_rows.append(
            {
                "THREAD_ID": md.thread_id,
                "MESSAGE_ID": m.message_id,
                "PARENT_ID": m.parent_id,
                "ROLE": m.role,
                "MESSAGE_PAYLOAD": m.message_payload,
                "REQUEST_ID": m.request_id,
                "CREATED_ON": _ts_from_ms(m.created_on_ms),
                "INGESTED_AT": now,
            }
        )

    if msg_rows:
        session.create_dataframe(msg_rows).write.mode("append").save_as_table(
            messages_table
        )

    _dedupe_thread_cache(session, settings, thread_id=md.thread_id)


def cache_conversation_mapping(
    session: Session,
    settings: Settings,
    *,
    conversation_id: str,
    thread_id: int,
    last_assistant_message_id: int | None,
) -> None:
    """Upsert a mapping between an app conversation and a Cortex thread."""
    table = f"{settings.database}.APP.CORTEX_CONVERSATIONS"
    now = datetime.now(UTC).replace(tzinfo=None)

    session.sql(
        f"""
MERGE INTO {table} t
USING (
  SELECT
    '{conversation_id}' AS CONVERSATION_ID,
    {thread_id} AS THREAD_ID,
    {last_assistant_message_id if last_assistant_message_id is not None else "NULL"} AS LAST_ASSISTANT_MESSAGE_ID,
    '{settings.cortex_origin_application}' AS ORIGIN_APPLICATION,
    TO_TIMESTAMP_NTZ('{now.isoformat()}') AS UPDATED_AT
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
  TO_TIMESTAMP_NTZ('{now.isoformat()}'),
  s.UPDATED_AT
);
"""  # noqa: S608
    ).collect()


def _dedupe_thread_cache(
    session: Session, settings: Settings, *, thread_id: int
) -> None:
    threads_table = f"{settings.database}.APP.CORTEX_THREADS"
    messages_table = f"{settings.database}.APP.CORTEX_THREAD_MESSAGES"

    session.sql(
        f"""
DELETE FROM {threads_table} t
USING (
  SELECT THREAD_ID, MAX(INGESTED_AT) AS KEEP_AT
  FROM {threads_table}
  WHERE THREAD_ID = {thread_id}
  GROUP BY THREAD_ID
  HAVING COUNT(*) > 1
) d
WHERE t.THREAD_ID = d.THREAD_ID
  AND t.INGESTED_AT < d.KEEP_AT;
"""  # noqa: S608
    ).collect()

    session.sql(
        f"""
DELETE FROM {messages_table} t
USING (
  SELECT THREAD_ID, MESSAGE_ID, MAX(INGESTED_AT) AS KEEP_AT
  FROM {messages_table}
  WHERE THREAD_ID = {thread_id}
  GROUP BY THREAD_ID, MESSAGE_ID
  HAVING COUNT(*) > 1
) d
WHERE t.THREAD_ID = d.THREAD_ID
  AND t.MESSAGE_ID = d.MESSAGE_ID
  AND t.INGESTED_AT < d.KEEP_AT;
"""  # noqa: S608
    ).collect()
