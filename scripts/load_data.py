"""Load CSV data into Snowflake stage and trigger ingestion.

Optional helper script.
Normally, data loading is done via Snowsight SQL worksheet or a notebook.
But if we want to automate it from Python:
- upload CSV to a stage
- run COPY INTO
This script intentionally leaves those details to the environment constraints.
"""


from pathlib import Path

from snowflake.snowpark import Session

from src.support_agent.config import get_settings
from src.support_agent.snowflake_client import create_snowpark_session

FILE_NOT_FOUND_MSG = "not found"
CSV_NOT_FOUND_MSG = "CSV file not found"


def execute_sql_file(session: Session, sql_file: Path) -> None:
    """Execute SQL statements from a file, one by one."""
    if not sql_file.exists():
        msg = f"{sql_file} {FILE_NOT_FOUND_MSG}"
        raise FileNotFoundError(msg)

    sql_content = sql_file.read_text()
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    for stmt in statements:
        session.sql(stmt).collect()

    print(f"✅ Executed SQL file: {sql_file.name}")


def upload_csv_to_stage(
    session: Session,
    csv_path: Path,
    stage_name: str,
) -> list:
    """Upload CSV file to Snowflake internal stage."""
    if not csv_path.exists():
        msg = f"{CSV_NOT_FOUND_MSG}: {csv_path}"
        raise FileNotFoundError(msg)

    # PUT command requires absolute path
    absolute_path = csv_path.absolute()
    put_command = (
        f"PUT file://{absolute_path} @{stage_name} "
        f"AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
    )

    print(f"📤 Uploading {csv_path.name} to stage {stage_name}...")
    result = session.sql(put_command).collect()
    print(f"✅ Upload complete: {result}")

    return result


def main() -> None:
    """Execute data loading."""
    settings = get_settings()
    session = create_snowpark_session(settings)

    base_dir = Path(__file__).resolve().parent.parent

    # SQL files
    sql_setup_path = base_dir / "sql" / "00_setup.sql"
    sql_ingest_path = base_dir / "sql" / "10_ingest.sql"

    # CSV file
    csv_path = base_dir / "data" / "tickets_clean.csv"

    # Step 1: Run setup SQL (creates database, schema, warehouse)
    print("\n🔧 Step 1: Running setup SQL...")
    execute_sql_file(session, sql_setup_path)

    # Step 2: Upload CSV to stage
    print("\n📤 Step 2: Uploading CSV file...")
    upload_csv_to_stage(session, csv_path, "support_data_stage")

    # Step 3: Run COPY INTO
    print("\n📥 Step 3: Loading data into table...")
    execute_sql_file(session, sql_ingest_path)

    session.close()


if __name__ == "__main__":
    main()
