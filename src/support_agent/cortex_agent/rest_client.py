"""Snowflake Cortex Agents REST API client.

This module implements:
- Threads API: create/list/describe/update/delete threads
- Agent Run API: `agent:run` (with an agent object or without)

It is designed for local apps (e.g., Streamlit) that can hold a Snowflake REST
token (PAT/OAuth/JWT) and call Snowflake's REST endpoints.

Docs:
- Threads: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-threads-rest-api
- Agent run: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
import json
import logging
from typing import Any

import requests


class CortexAgentsRestError(RuntimeError):
    """Raised when the Cortex Agents REST API returns an error."""

    def __init__(
        self,
        *,
        kind: str,
        status_code: int | None = None,
        details: str | None = None,
    ) -> None:
        msg = kind
        if status_code is not None:
            msg = f"{msg} (HTTP {status_code})"
        if details:
            msg = f"{msg}: {details}"
        super().__init__(msg)


class MissingSnowflakeAccountUrlError(ValueError):
    """Raised when the Snowflake account URL is not configured."""

    def __init__(self) -> None:
        super().__init(
            "Missing Snowflake account URL. Set SNOWFLAKE_ACCOUNT_URL."
        )


class MissingSnowflakeRestTokenError(ValueError):
    """Raised when the Snowflake REST token is not configured."""

    def __init__(self) -> None:
        super().__init(
            "Missing Snowflake REST token. Set SNOWFLAKE_REST_TOKEN."
        )


class MissingParentMessageIdError(ValueError):
    """Raised when a thread is used without a parent message id."""

    def __init__(self) -> None:
        super().__init("parent_message_id is required when thread_id is set")


@dataclass(frozen=True)
class ThreadMetadata:
    """Thread metadata as returned by the Threads API."""

    thread_id: int
    thread_name: str | None = None
    origin_application: str | None = None
    created_on_ms: int | None = None
    updated_on_ms: int | None = None


@dataclass(frozen=True)
class ThreadMessage:
    """Message as returned by the Threads API."""

    message_id: int
    parent_id: int | None
    created_on_ms: int | None
    role: str
    message_payload: str
    request_id: str | None


@dataclass(frozen=True)
class ThreadDescribe:
    """Thread description: metadata plus a batch of messages."""

    metadata: ThreadMetadata
    messages: list[ThreadMessage]


@dataclass(frozen=True)
class AgentRunResult:
    """Result of a single `agent:run` call."""

    assistant_text: str
    user_message_id: int | None = None
    assistant_message_id: int | None = None
    raw_response: dict[str, Any] | None = None


def _normalize_account_url(account_url: str) -> str:
    url = (account_url or "").strip()
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url.rstrip("/")
    host = url.rstrip("/")
    if "snowflakecomputing.com" not in host:
        host = f"{host}.snowflakecomputing.com"
    return f"https://{host}"


def _iter_sse_events(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
    """Parse Server-Sent Events into (event_type, data_str) tuples."""
    event_type = "message"
    data_parts: list[str] = []

    for raw_line in lines:
        line = raw_line.rstrip("\r")
        if not line:
            if data_parts:
                yield event_type, "\n".join(data_parts)
            event_type = "message"
            data_parts = []
            continue

        if line.startswith(":"):
            continue

        if line.startswith("event:"):
            event_type = line[len("event:") :].strip() or "message"
            continue

        if line.startswith("data:"):
            data_parts.append(line[len("data:") :].lstrip())
            continue

    if data_parts:
        yield event_type, "\n".join(data_parts)


def _extract_assistant_text_from_response(payload: dict[str, Any]) -> str:
    """Extract a user-visible assistant text from a `response` payload."""
    content = payload.get("content") or []
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            txt = item.get("text")
            if isinstance(txt, str) and txt:
                parts.append(txt)

    return "\n".join(parts).strip()


class CortexAgentsRestClient:
    """Minimal REST client for Snowflake Cortex Agents + Threads APIs."""

    def __init__(
        self,
        *,
        account_url: str,
        token: str,
        origin_application: str | None = None,
        timeout_s: float = 60.0,
    ) -> None:
        self._account_url = _normalize_account_url(account_url)
        self._token = (token or "").strip()
        self._origin_application = (origin_application or "").strip() or None
        self._timeout_s = timeout_s

        if not self._account_url:
            raise MissingSnowflakeAccountUrlError()
        if not self._token:
            raise MissingSnowflakeRestTokenError()

    def _headers(self, *, accept: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        if accept:
            headers["Accept"] = accept
        return headers

    def _url(self, path: str) -> str:
        return f"{self._account_url}{path}"

    def _raise_for_error(self, response: requests.Response) -> None:
        if response.ok:
            return
        text = ""
        try:
            text = response.text
        except Exception:
            text = ""
        raise CortexAgentsRestError(
            kind="cortex_agents_rest_api_error",
            status_code=response.status_code,
            details=text,
        )

    # -----------------
    # Threads API
    # -----------------
    def create_thread(self, *, origin_application: str | None = None) -> int:
        """Create a new thread and return its thread id."""
        payload: dict[str, Any] = {}
        origin = (
            (origin_application or "").strip()
            or (self._origin_application or "")
        ).strip()
        if origin:
            payload["origin_application"] = origin

        resp = requests.post(
            self._url("/api/v2/cortex/threads"),
            headers=self._headers(accept="application/json"),
            json=payload or {},
            timeout=self._timeout_s,
        )
        self._raise_for_error(resp)

        response = resp.json()

        # Handle different response formats:
        # - Older API: returns just thread_id as int/string
        # - Newer API: returns full object with thread_id field
        if isinstance(response, dict) and "thread_id" in response:
            thread_id = response["thread_id"]
        else:
            thread_id = response

        if isinstance(thread_id, str):
            thread_id = thread_id.strip().strip('"')
        try:
            return int(thread_id)
        except Exception as e:
            raise CortexAgentsRestError(
                kind="unexpected_create_thread_response",
                details=repr(response),
            ) from e

    def list_threads(
        self, *, origin_application: str | None = None
    ) -> list[ThreadMetadata]:
        """List all threads available to the caller."""
        params: dict[str, str] = {}
        if origin_application:
            params["origin_application"] = origin_application

        resp = requests.get(
            self._url("/api/v2/cortex/threads"),
            headers=self._headers(accept="application/json"),
            params=params or None,
            timeout=self._timeout_s,
        )
        self._raise_for_error(resp)

        data = resp.json()
        if not isinstance(data, list):
            raise CortexAgentsRestError(
                kind="unexpected_list_threads_response",
                details=repr(data),
            )

        out: list[ThreadMetadata] = []
        for item in data:
            if not isinstance(item, dict) or "thread_id" not in item:
                continue
            out.append(
                ThreadMetadata(
                    thread_id=int(item["thread_id"]),
                    thread_name=item.get("thread_name"),
                    origin_application=item.get("origin_application"),
                    created_on_ms=item.get("created_on"),
                    updated_on_ms=item.get("updated_on"),
                )
            )
        return out

    def describe_thread(
        self,
        thread_id: int,
        *,
        page_size: int = 20,
        last_message_id: int | None = None,
    ) -> ThreadDescribe:
        """Describe a thread and return a batch of its messages."""
        params: dict[str, Any] = {"page_size": page_size}
        if last_message_id is not None:
            params["last_message_id"] = last_message_id

        resp = requests.get(
            self._url(f"/api/v2/cortex/threads/{thread_id}"),
            headers=self._headers(accept="application/json"),
            params=params,
            timeout=self._timeout_s,
        )
        self._raise_for_error(resp)

        body = resp.json()
        if not isinstance(body, dict):
            raise CortexAgentsRestError(
                kind="unexpected_describe_thread_response",
                details=repr(body),
            )

        md = body.get("metadata")
        if not isinstance(md, dict) or "thread_id" not in md:
            raise CortexAgentsRestError(
                kind="missing_thread_metadata",
                details=repr(body),
            )

        metadata = ThreadMetadata(
            thread_id=int(md["thread_id"]),
            thread_name=md.get("thread_name"),
            origin_application=md.get("origin_application"),
            created_on_ms=md.get("created_on"),
            updated_on_ms=md.get("updated_on"),
        )

        messages_in = body.get("messages") or []
        if not isinstance(messages_in, list):
            messages_in = []

        messages: list[ThreadMessage] = []
        for m in messages_in:
            if not isinstance(m, dict) or "message_id" not in m:
                continue
            messages.append(
                ThreadMessage(
                    message_id=int(m["message_id"]),
                    parent_id=(
                        int(m["parent_id"]) if m.get("parent_id") else None
                    ),
                    created_on_ms=m.get("created_on"),
                    role=str(m.get("role") or ""),
                    message_payload=str(m.get("message_payload") or ""),
                    request_id=m.get("request_id"),
                )
            )

        return ThreadDescribe(metadata=metadata, messages=messages)

    def update_thread(
        self, thread_id: int, *, thread_name: str
    ) -> dict[str, Any]:
        """Update the thread's name."""
        resp = requests.post(
            self._url(f"/api/v2/cortex/threads/{thread_id}"),
            headers=self._headers(accept="application/json"),
            json={"thread_name": thread_name},
            timeout=self._timeout_s,
        )
        self._raise_for_error(resp)
        data = resp.json()
        if not isinstance(data, dict):
            raise CortexAgentsRestError(
                kind="unexpected_update_thread_response",
                details=repr(data),
            )
        return data

    def delete_thread(self, thread_id: int) -> bool:
        """Delete a thread and all messages in it."""
        resp = requests.delete(
            self._url(f"/api/v2/cortex/threads/{thread_id}"),
            headers=self._headers(accept="application/json"),
            timeout=self._timeout_s,
        )
        self._raise_for_error(resp)
        data = resp.json()
        return bool(data.get("success")) if isinstance(data, dict) else False

    # -----------------
    # Agent Run API
    # -----------------
    def run_agent_with_object(
        self,
        *,
        database: str,
        schema: str,
        agent_name: str,
        user_text: str,
        thread_id: int | None = None,
        parent_message_id: int | None = None,
        stream: bool | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        """Run `agent:run` against an existing agent object."""
        path = f"/api/v2/databases/{database}/schemas/{schema}/agents/{agent_name}:run"
        return self._run_agent(
            path=path,
            user_text=user_text,
            thread_id=thread_id,
            parent_message_id=parent_message_id,
            stream=stream,
            tool_choice=tool_choice,
        )

    def run_agent_with_object_messages(
        self,
        *,
        database: str,
        schema: str,
        agent_name: str,
        messages: list[dict[str, Any]],
        stream: bool | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        """Run `agent:run` against an existing agent object with full chat history.

        Use this when Threads is unavailable: omit `thread_id` and send the full
        conversation in the `messages` array.
        """
        path = f"/api/v2/databases/{database}/schemas/{schema}/agents/{agent_name}:run"
        return self._run_agent_messages(
            path=path,
            messages=messages,
            stream=stream,
            tool_choice=tool_choice,
        )

    def run_agent_without_object(
        self,
        *,
        user_text: str,
        agent_config: dict[str, Any],
        thread_id: int | None = None,
        parent_message_id: int | None = None,
        stream: bool | None = None,
        tool_choice: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        """Run `agent:run` without creating an agent object."""
        payload = dict(agent_config)
        return self._run_agent(
            path="/api/v2/cortex/agent:run",
            user_text=user_text,
            thread_id=thread_id,
            parent_message_id=parent_message_id,
            stream=stream,
            tool_choice=tool_choice,
            extra_payload=payload,
        )

    def _run_agent(
        self,
        *,
        path: str,
        user_text: str,
        thread_id: int | None,
        parent_message_id: int | None,
        stream: bool | None,
        tool_choice: dict[str, Any] | None,
        extra_payload: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        payload: dict[str, Any] = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_text}],
                }
            ]
        }

        if thread_id is not None:
            if parent_message_id is None:
                raise MissingParentMessageIdError()
            payload["thread_id"] = thread_id
            payload["parent_message_id"] = parent_message_id

        if stream is not None:
            payload["stream"] = bool(stream)

        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        if extra_payload:
            payload.update(extra_payload)

        want_stream = payload.get("stream", True)
        accept = "text/event-stream" if want_stream else "application/json"

        resp = requests.post(
            self._url(path),
            headers=self._headers(accept=accept),
            json=payload,
            timeout=self._timeout_s,
            stream=bool(want_stream),
        )
        self._raise_for_error(resp)

        if not want_stream:
            data = resp.json()
            if not isinstance(data, dict):
                raise CortexAgentsRestError(
                    kind="unexpected_non_streaming_agent_response",
                    details=repr(data),
                )
            return AgentRunResult(
                assistant_text=_extract_assistant_text_from_response(data),
                raw_response=data,
            )

        user_mid: int | None = None
        assistant_mid: int | None = None
        final_response: dict[str, Any] | None = None

        for event_type, data_str in _iter_sse_events(
            resp.iter_lines(decode_unicode=True)
        ):
            if not data_str:
                continue

            if event_type == "metadata":
                try:
                    data = json.loads(data_str)
                    md = (
                        data.get("metadata") if isinstance(data, dict) else None
                    )
                    if isinstance(md, dict):
                        role = md.get("role")
                        mid = md.get("message_id")
                        if role == "user":
                            user_mid = int(mid)
                        elif role == "assistant":
                            assistant_mid = int(mid)
                except Exception as exc:
                    logging.debug(
                        "Failed to parse metadata event", exc_info=exc
                    )
                    continue

            if event_type == "response":
                try:
                    data = json.loads(data_str)
                    if isinstance(data, dict):
                        final_response = data
                except Exception as exc:
                    logging.debug(
                        "Failed to parse response event", exc_info=exc
                    )
                    continue

        if final_response is None:
            raise CortexAgentsRestError(
                kind="missing_streaming_final_response_event"
            )

        return AgentRunResult(
            assistant_text=_extract_assistant_text_from_response(
                final_response
            ),
            user_message_id=user_mid,
            assistant_message_id=assistant_mid,
            raw_response=final_response,
        )

    def _run_agent_messages(
        self,
        *,
        path: str,
        messages: list[dict[str, Any]],
        stream: bool | None,
        tool_choice: dict[str, Any] | None,
        extra_payload: dict[str, Any] | None = None,
    ) -> AgentRunResult:
        payload: dict[str, Any] = {"messages": messages}
        if stream is not None:
            payload["stream"] = bool(stream)
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if extra_payload:
            payload.update(extra_payload)

        want_stream = payload.get("stream", True)
        accept = "text/event-stream" if want_stream else "application/json"

        resp = requests.post(
            self._url(path),
            headers=self._headers(accept=accept),
            json=payload,
            timeout=self._timeout_s,
            stream=bool(want_stream),
        )
        self._raise_for_error(resp)

        if not want_stream:
            data = resp.json()
            if not isinstance(data, dict):
                raise CortexAgentsRestError(
                    kind="unexpected_non_streaming_agent_response",
                    details=repr(data),
                )
            return AgentRunResult(
                assistant_text=_extract_assistant_text_from_response(data),
                raw_response=data,
            )

        final_response: dict[str, Any] | None = None
        for event_type, data_str in _iter_sse_events(
            resp.iter_lines(decode_unicode=True)
        ):
            if not data_str:
                continue
            if event_type == "response":
                try:
                    data = json.loads(data_str)
                    if isinstance(data, dict):
                        final_response = data
                except Exception as exc:
                    logging.debug(
                        "Failed to parse response event", exc_info=exc
                    )
                    continue

        if final_response is None:
            raise CortexAgentsRestError(
                kind="missing_streaming_final_response_event"
            )

        return AgentRunResult(
            assistant_text=_extract_assistant_text_from_response(
                final_response
            ),
            raw_response=final_response,
        )
