"""Write agent outputs to Snowflake tables."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from snowflake.snowpark import Session

from ..config import Settings
from ..graph.state import TicketState


def write_agent_output(
    session: Session, settings: Settings, state: TicketState
) -> str:
    """Persist agent output into PROJECT_DB.APP.AGENT_OUTPUTS (create via sql/40_eval_tables.sql)."""
    output_id = str(uuid.uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)

    table = f"{settings.database}.APP.AGENT_OUTPUTS"
    row: dict[str, Any] = {
        "OUTPUT_ID": output_id,
        "TICKET_ID": state.get("ticket_id"),
        "ISSUE_DESCRIPTION": state.get("issue_description"),
        "PREDICTED_PRIORITY": state.get("priority_level"),
        "RETRIEVED_CONTEXT": state.get("retrieved_context"),
        "RESPONSE": state.get("final_response"),
        "CREATED_AT": now,
    }

    df = session.create_dataframe([row])
    df.write.mode("append").save_as_table(table)
    return output_id
