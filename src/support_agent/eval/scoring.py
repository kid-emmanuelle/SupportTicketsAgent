"""Metrics calculation and LLM judge prompts."""

from __future__ import annotations

from typing import Any


def basic_scores(*, retrieved_count: int, response: str) -> dict[str, Any]:
    """Minimal non-LLM scoring placeholders."""
    return {
        "retrieved_count": retrieved_count,
        "response_nonempty": bool(response and response.strip()),
        "response_length": len(response or ""),
    }
