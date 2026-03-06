"""Build Cortex Agent and Thread manager."""

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.utils import execute_sql_file
from src.support_agent.config import get_settings
from src.support_agent.snowflake_client import create_snowpark_session


def main() -> None:
    """Execute data loading."""
    settings = get_settings()
    session = create_snowpark_session(settings)

    base_dir = Path(__file__).resolve().parent.parent / "sql"

    # SQL files
    sql_file_name = ["35_create_agent.sql", "45_cortex_threads_history.sql"]
    for file_name in sql_file_name:
        file_path = base_dir / file_name
        execute_sql_file(session, file_path)

    session.close()


if __name__ == "__main__":
    main()
