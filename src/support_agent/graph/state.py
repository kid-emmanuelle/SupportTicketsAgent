"""State definitions for the support agent graph module."""

from __future__ import annotations

from typing import Any, TypedDict


class TicketState(TypedDict, total=False):
    """TypedDict representing the state of a support ticket as it moves through the agent graph."""

    # Input
    ticket_id: str
    issue_description: str
    language: str

    # Derived
    topic: str
    intent: str
    priority_level: str

    # Retrieval + response
    retrieved_context: list[str]
    final_response: str

    # Debug / metadata
    retrieved_raw: list[dict[str, Any]]
