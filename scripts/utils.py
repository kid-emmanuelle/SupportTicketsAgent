""" Utilities for scripts python file """

from pathlib import Path
from snowflake.snowpark import Session


def execute_sql_file(session: Session, sql_file: Path) -> None:
    """Execute SQL file safely (handles -- comments and semicolons in strings)."""
    if not sql_file.exists():
        print(f"{sql_file} not found.")
        return

    sql = sql_file.read_text(encoding="utf-8")

    statements = []
    current = []
    in_string = False

    for line in sql.splitlines():
        stripped = line.strip()

        # Skip full-line comments
        if stripped.startswith("--"):
            continue

        for char in line:
            if char == "'":
                in_string = not in_string

            if char == ";" and not in_string:
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(char)

        current.append("\n")

    # Last statement
    final_stmt = "".join(current).strip()
    if final_stmt:
        statements.append(final_stmt)

    for stmt in statements:
        session.sql(stmt).collect()

    print(f"✅ Executed SQL file: {sql_file.name}")
