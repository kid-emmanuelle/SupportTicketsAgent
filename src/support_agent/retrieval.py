"""Cortex Search wrapper for semantic retrieval."""

from __future__ import annotations

from typing import Any

from snowflake.core import Root
from snowflake.snowpark import Session

from .config import Settings


def retrieve_context(
    session: Session,
    settings: Settings,
    query: str,
    *,
    columns: list[str] | None = None,
    limit: int | None = None,
    filters: dict[str, Any] | None = None,
) -> list[dict]:
    """Query a Cortex Search service and return raw results.

    - `columns` should include the text you want (e.g., ['body_answer'] or ['chunk_text']).
    - `filters` can be used if your service supports attributes (e.g., {'language': 'fr'}).
    """
    columns = columns or ["body_answer"]
    limit = limit or settings.top_k

    root = Root(session)
    svc = (
        root.databases[settings.search_db]
        .schemas[settings.search_schema]
        .cortex_search_services[settings.search_service]
    )

    kwargs = {"query": query, "columns": columns, "limit": limit}
    if filters:
        kwargs["filter"] = (
            filters  # depending on your SDK version, this may differ
        )

    resp = svc.search(**kwargs)
    return list(resp.results or [])


def retrieve_text_chunks(
    session: Session, settings: Settings, query: str
) -> list[str]:
    """Convenience wrapper returning only the primary text field."""
    results = retrieve_context(
        session, settings, query, columns=["body_answer"]
    )
    out: list[str] = []
    for r in results:
        if r.get("body_answer"):
            out.append(str(r["body_answer"]))
    return out
