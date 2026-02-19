"""Cortex client module."""

from __future__ import annotations

import re

from snowflake.snowpark import Session
from snowflake.snowpark.functions import lit


class CortexAgentError(RuntimeError):
    """Base exception for Cortex Agent call failures."""


class CortexAgentNoResultError(CortexAgentError):
    """Raised when a Cortex Agent call returns no rows."""

    def __init__(self) -> None:
        super().__init__("Cortex Agent returned no result.")


_IDENTIFIER_PART_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$]*$")


def _validate_identifier_part(value: str, *, label: str) -> str:
    if not _IDENTIFIER_PART_RE.fullmatch(value):
        msg = f"Invalid Snowflake identifier for {label!s}: {value!r}"
        raise ValueError(msg)
    return value


def call_cortex_agent(
    session: Session,
    database: str,
    schema: str,
    agent_name: str,
    user_message: str,
) -> str:
    """Calls a Snowflake Cortex Agent and returns the response text."""
    database = _validate_identifier_part(database, label="database")
    schema = _validate_identifier_part(schema, label="schema")
    agent_name = _validate_identifier_part(agent_name, label="agent_name")

    fully_qualified = f"{database}.{schema}.{agent_name}"

    result = session.table_function(
        fully_qualified, INPUT=lit(user_message)
    ).collect()

    if not result:
        raise CortexAgentNoResultError()

    return result[0]["RESPONSE"]
