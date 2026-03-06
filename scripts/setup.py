"""Run setup sql scripts and .env dependent scripts."""

from pathlib import Path
import re
import sys


sys.path.insert(0, str(Path(__file__).parent.parent))

from snowflake.snowpark import Session

from scripts.utils import execute_sql_file
from src.support_agent.config import Settings, get_settings
from src.support_agent.snowflake_client import create_snowpark_session


ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = ROOT / ".env.example"
ENV_OUT = ROOT / ".env"


def prompt(label: str, default: str = "") -> str:
    """Prompt the user for input with an optional default value.

    Args:
        label: The prompt message to display to the user.
        default: Optional default value to use if user provides no input.

    Returns:
        The user's input, or the default value if no input provided.
    """
    hint = f" [{default}]" if default else ""
    value = input(f"{label}{hint}: ").strip()
    return value or default


def fill_env(account: str, user: str, password: str, role: str) -> None:
    """Create or overwrite .env file with Snowflake credentials.

    Reads from .env.example template and replaces placeholders with actual values.
    Prompts for confirmation before overwriting existing .env file.

    Args:
        account: Snowflake account identifier.
        user: Snowflake username.
        password: Snowflake password.
        role: Snowflake role (e.g., ACCOUNTADMIN).

    Raises:
        SystemExit: If .env.example not found or user declines overwrite.
    """
    if not ENV_EXAMPLE.exists():
        print(f"Error: {ENV_EXAMPLE} not found.", file=sys.stderr)
        sys.exit(1)

    if ENV_OUT.exists():
        answer = (
            input(f"{ENV_OUT} already exists. Overwrite? [y/N] ")
            .strip()
            .lower()
        )
        if answer != "y":
            print("Aborted.")
            sys.exit(0)

    content = ENV_EXAMPLE.read_text()

    content = content.replace("<account_identifier>", account)

    replacements = {
        r"^(SNOWFLAKE_ACCOUNT\s*=).*$": rf"\g<1>{account}",
        r"^(SNOWFLAKE_USER\s*=).*$": rf"\g<1>{user}",
        r"^(SNOWFLAKE_PASSWORD\s*=).*$": rf"\g<1>{password}",
        r"^(SNOWFLAKE_ROLE\s*=).*$": rf"\g<1>{role}",
    }

    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    ENV_OUT.write_text(content)
    print(f".env written to {ENV_OUT}")


def get_pat_secret(
    session: Session, settings: Settings, n_days_to_expire: int = 30
) -> str:
    """Generate or rotate a Programmatic Access Token (PAT) for the user.

    Configures Cortex cross-region settings, network policies, and manages
    the PAT lifecycle. If a token exists, it rotates it; otherwise creates new.

    Args:
        session: Active Snowpark session.
        settings: Application settings containing user credentials.
        n_days_to_expire: Number of days until token expiration (default: 30).

    Returns:
        The secret value of the generated or rotated PAT.
    """
    # get .env user name
    user_name = settings.user.upper()
    token_name = user_name + "_" + "pat"

    # Enable all regions and add policy to user
    session.sql(
        "ALTER ACCOUNT SET CORTEX_ENABLED_CROSS_REGION = 'ANY_REGION'"
    ).collect()
    session.sql(
        "CREATE NETWORK POLICY IF NOT EXISTS cortex_policy ALLOWED_IP_LIST = ('0.0.0.0/0')"
    ).collect()
    session.sql(
        f"ALTER USER {user_name} SET NETWORK_POLICY = CORTEX_POLICY"
    ).collect()

    # Looking for existing pat
    query = f"SHOW USER PROGRAMMATIC ACCESS TOKENS FOR USER {user_name};"
    query_result = session.sql(query).collect()
    exist = False
    for existing_pat in query_result:
        if existing_pat.name.lower() == token_name.lower():
            exist = True

    # Rotate or create pat
    if exist:
        query = f"ALTER USER IF EXISTS {user_name} ROTATE PROGRAMMATIC ACCESS TOKEN {token_name};"
        query_result = session.sql(query).collect()
    else:
        query = f"ALTER USER IF EXISTS {user_name} ADD PROGRAMMATIC ACCESS TOKEN {token_name} DAYS_TO_EXPIRY = {n_days_to_expire};"
        query_result = session.sql(query).collect()

    # Return updated pat secret
    return query_result[0].token_secret


def main() -> None:
    """Execute complete Snowflake environment setup workflow.

    Performs the following steps:
    1. Collects Snowflake credentials and creates .env file
    2. Executes SQL setup scripts (warehouse, schema, tables, stage, policies)
    3. Generates programmatic access token and updates .env
    """
    # Step 1: Initialize .env file
    print("Step 1: Configure Snowflake credentials...\n")
    account = prompt("Snowflake account (e.g. xy12345-yi81042)")
    user = prompt("Snowflake user")
    password = prompt("Snowflake password")
    role = prompt("Snowflake role", default="ACCOUNTADMIN")

    if not account or not user or not password:
        print(
            "Error: account, user and password are required.", file=sys.stderr
        )
        sys.exit(1)

    fill_env(account, user, password, role)

    # Load .env variables
    settings = get_settings()
    session = create_snowpark_session(settings)

    # Get project src directory path
    base_dir = Path(__file__).resolve().parent.parent

    # SQL files
    sql_file_name = "00_setup.sql"
    sql_path = base_dir / "sql" / sql_file_name

    # Step 2: Run setup file (warehouse, schema, table, stage creation, policy creation)
    print("\nStep 2: Run setup file...")
    execute_sql_file(session, sql_path)

    # Step 3: Create Programmatic access token
    print("\nStep 3: Create and get programmatic access token secret...")
    pat_secret = get_pat_secret(session, settings)

    # Write pat_secret to .env: update <token> statement
    content = ENV_OUT.read_text()
    content = content.replace("<token>", pat_secret)
    ENV_OUT.write_text(content)

    session.close()


if __name__ == "__main__":
    main()
