import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from snowflake.connector.pandas_tools import write_pandas
from src.support_agent.snowflake_client import connect_snowflake

# -------------------------
# Config
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # base = project root
CSV_PATH = BASE_DIR / "data" / "tickets_clean.csv"
SQL_SETUP_PATH = BASE_DIR / "sql" / "00_setup.sql"
TABLE_NAME = "SUPPORT_TICKETS"
SCHEMA = "RAW"

# -------------------------
# SQL execution
# -------------------------
def execute_sql_file(conn, sql_file: Path):
    if not sql_file.exists():
        raise FileNotFoundError(f"{sql_file} not found")

    sql_content = sql_file.read_text()

    # Split statements by ";" and strip
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

    with conn.cursor() as cur:
        for stmt in statements:
            cur.execute(stmt)

    print(f"✅ Executed SQL file: {sql_file.name}")


# -------------------------
# Load CSV into Snowflake
# -------------------------
def load_csv_to_snowflake(conn, csv_path: Path, table_name: str, schema: str, overwrite: bool = True):
    if not csv_path.exists():
        raise FileNotFoundError(f"{csv_path} not found")

    df = pd.read_csv(csv_path)

    success, nchunks, nrows, _ = write_pandas(
        conn=conn,
        df=df,
        table_name=table_name,
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=schema,
        overwrite=overwrite,
        auto_create_table=True,
    )

    print(f"✅ Load success={success} | rows={nrows} | chunks={nchunks}")


# -------------------------
# Main
# -------------------------
def main():
    # Charger .env
    load_dotenv()

    # 1️⃣ Création d'une connexion unique
    conn = connect_snowflake()

    try:
        # 2️⃣ Exécution du script SQL de setup
        execute_sql_file(conn, SQL_SETUP_PATH)

        # 3️⃣ Chargement CSV dans Snowflake
        load_csv_to_snowflake(conn, CSV_PATH, TABLE_NAME, SCHEMA, overwrite=True)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
