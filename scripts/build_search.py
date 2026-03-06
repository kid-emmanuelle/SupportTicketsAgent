""" Build a Cortex Search Service on curated ticket table."""

import os


os.environ["SF_OCSP_FAIL_OPEN"] = "true"
os.environ["SF_OCSP_RESPONSE_CACHE_SERVER_ENABLED"] = "false"

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

    base_dir = Path(__file__).resolve().parent.parent

    # SQL files
    sql_curate_path = base_dir / "sql" / "20_curate.sql"
    sql_search_service_path = base_dir / "sql" / "30_search_service.sql"

    # Step 1: Run curated table creation and process
    print("\nStep 1: Running curate table process...")
    execute_sql_file(session, sql_curate_path)

    # Step 2: Build cortex search service
    print("\nStep 2: Building cortex search service...")
    execute_sql_file(session, sql_search_service_path)

    session.close()


if __name__ == "__main__":
    main()
