from __future__ import annotations

from snowflake.snowpark import Session
from snowflake.core import Root

from .config import Settings


def create_snowpark_session(settings: Settings) -> Session:
    """Create a Snowpark Session using password auth (adapt for key-pair if needed)."""
    connection_parameters = {
        "account": settings.account,
        "user": settings.user,
        "password": settings.password,
        "role": settings.role or None,
        "warehouse": settings.warehouse or None,
        "database": settings.database or None,
        "schema": settings.schema or None,
    }
    # Remove None values to avoid Snowpark complaints in some environments
    connection_parameters = {k: v for k, v in connection_parameters.items() if v is not None}
    return Session.builder.configs(connection_parameters).create()


def get_root(session: Session) -> Root:
    return Root(session)