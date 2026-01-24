"""Load CSV data into Snowflake stage and trigger ingestion.
Optional helper script.
Normally, data loading is done via Snowsight SQL worksheet or a notebook.
But if we want to automate it from Python:
- upload CSV to a stage
- run COPY INTO
This script intentionally leaves those details to the environment constraints.
"""
from __future__ import annotations
from src.support_agent.snowflake_client import create_snowpark_session
from src.support_agent.config import get_settings
from pathlib import Path

def execute_sql_file(session, sql_file: Path):
    """Execute SQL statements from a file, one by one."""
    if not sql_file.exists():
        raise FileNotFoundError(f"{sql_file} not found")
    
    sql_content = sql_file.read_text()
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
    
    for stmt in statements:
        print(f"Executing: {stmt[:100]}...")
        session.sql(stmt).collect()
    
    print(f"✅ Executed SQL file: {sql_file.name}")

def upload_csv_to_stage(session, csv_path: Path, stage_name: str):
    """Upload CSV file to Snowflake internal stage."""
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # PUT command requires absolute path
    absolute_path = csv_path.absolute()
    put_command = f"PUT file://{absolute_path} @{stage_name} AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
    
    print(f"📤 Uploading {csv_path.name} to stage {stage_name}...")
    result = session.sql(put_command).collect()
    print(f"✅ Upload complete: {result}")
    
    return result

def main():
    """Execute data loading."""
    settings = get_settings()
    session = create_snowpark_session(settings)
    
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # SQL files
    SQL_SETUP_PATH = BASE_DIR / "sql" / "00_setup.sql"
    SQL_INGEST_PATH = BASE_DIR / "sql" / "10_ingest.sql"
    
    # CSV file
    CSV_PATH = BASE_DIR / "data" / "tickets_clean.csv"
    
    # Step 1: Run setup SQL (creates database, schema, warehouse)
    print("\n🔧 Step 1: Running setup SQL...")
    #execute_sql_file(session, SQL_SETUP_PATH)
    
    # Step 2: Upload CSV to stage
    print("\n📤 Step 2: Uploading CSV file...")
    #upload_csv_to_stage(session, CSV_PATH, "support_data_stage")
    
    # Step 3: Run COPY INTO
    print("\n📥 Step 3: Loading data into table...")
    execute_sql_file(session, SQL_INGEST_PATH)
    
    session.close()

if __name__ == "__main__":
    main()