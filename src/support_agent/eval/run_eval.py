"""Batch evaluation runner."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from snowflake.snowpark import Session

from ..config import Settings
from ..graph.build import build_graph
from .scoring import basic_scores


def create_run_id() -> str:
    """Create a unique run ID."""
    return str(uuid.uuid4())


def write_run_metadata(
    session: Session,
    settings: Settings,
    *,
    run_id: str,
    commit_sha: str,
    notes: str = "",
):
    """Write metadata about an evaluation run to the database."""
    table = f"{settings.database}.EVAL.RUNS"
    now = datetime.now(UTC).replace(tzinfo=None)
    row = {
        "RUN_ID": run_id,
        "CREATED_AT": now,
        "COMMIT_SHA": commit_sha,
        "MODEL": settings.llm_model,
        "NOTES": notes,
    }
    session.create_dataframe([row]).write.mode("append").save_as_table(table)


def write_eval_result(
    session: Session, settings: Settings, row: dict[str, Any]
):
    """Write a single evaluation result to the database."""
    table = f"{settings.database}.EVAL.RESULTS"
    session.create_dataframe([row]).write.mode("append").save_as_table(table)


def run_batch_eval(
    session: Session,
    settings: Settings,
    issues: list[dict[str, Any]],
    *,
    run_id: str | None = None,
    commit_sha: str = "unknown",
    notes: str = "",
) -> str:
    """Run a batch evaluation on a list of issues."""
    run_id = run_id or create_run_id()
    write_run_metadata(
        session, settings, run_id=run_id, commit_sha=commit_sha, notes=notes
    )

    agent = build_graph(session=session, settings=settings)
    now = datetime.now(UTC).replace(tzinfo=None)

    for item in issues:
        state = {
            "ticket_id": item.get("ticket_id", ""),
            "language": item.get("language", ""),
            "issue_description": item["issue_description"],
        }
        out = agent.invoke(state)
        scores = basic_scores(
            retrieved_count=len(out.get("retrieved_context", []) or []),
            response=out.get("final_response", ""),
        )

        eval_row = {
            "RUN_ID": run_id,
            "TICKET_ID": state.get("ticket_id"),
            "LANGUAGE": state.get("language"),
            "ISSUE_DESCRIPTION": state.get("issue_description"),
            "PREDICTED_PRIORITY": out.get("priority_level"),
            "RETRIEVED_COUNT": len(out.get("retrieved_context", []) or []),
            "RESPONSE": out.get("final_response"),
            "SCORES": scores,
            "CREATED_AT": now,
        }
        write_eval_result(session, settings, eval_row)

    return run_id
