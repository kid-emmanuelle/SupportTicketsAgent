"""Process and clean support tickets data with configurable rules.

This script:
1. Loads raw tickets from Snowflake
2. Applies configurable cleaning rules
3. Saves cleaned data to curated schema
"""

from pathlib import Path
import sys

import pandas as pd
from snowflake.snowpark.session import Session

from src.support_agent.config import get_settings
from src.support_agent.snowflake_client import create_snowpark_session


current_file_path = Path().resolve()
sys.path.insert(0, str(current_file_path))


# ============================================================================
# CONFIGURATION - Adjust these rules as needed
# ============================================================================

CLEANING_RULES = {
    # Minimum character length thresholds
    "min_body_length": 50,
    "min_answer_length": 50,
    # Columns to exclude (e.g., tag columns)
    "exclude_column_patterns": ["tag"],
    "exclude_column_name": ["version"],
    # Whether to remove duplicates
    "remove_duplicates": True,
    "duplicate_columns": ["body", "answer"],
    # Source and target tables
    "source_table": "PROJECT_DB.RAW.SUPPORT_TICKETS",
    "target_schema": "PROJECT_DB.CURATED",
    "target_table": "PROJECT_DB.CURATED.TICKETS_CLEANED",
}


# ============================================================================
# Processing Functions
# ============================================================================


def load_raw_data(session: Session, source_table: str) -> pd.DataFrame:
    """Load raw tickets data from Snowflake."""
    query = f"""
    SELECT
        SUBJECT,
        BODY,
        ANSWER,
        TYPE,
        QUEUE,
        PRIORITY,
        LANGUAGE,
        VERSION,
        TAG_1,
        TAG_2,
        TAG_3,
        TAG_4,
        TAG_5,
        TAG_6,
        TAG_7,
        TAG_8
    FROM '{source_table}'"""
    return session.sql(query).to_pandas().rename(columns=lambda s: s.lower())


def apply_column_filters(
    df: pd.DataFrame, exclude_patterns: list, exclude_column: list
) -> pd.DataFrame:
    """Remove columns matching exclude patterns."""
    cols = [
        col
        for col in df.columns[1:]
        if not any(pattern in col for pattern in exclude_patterns)
        and col not in exclude_column
    ]
    return df.loc[:, cols].copy()


def apply_length_filters(
    df: pd.DataFrame, min_body_length: int, min_answer_length: int
) -> pd.DataFrame:
    """Filter out tickets with body or answer below minimum length."""
    return df[
        (df["body"].str.len() >= min_body_length)
        & (df["answer"].str.len() >= min_answer_length)
    ].copy()


def save_to_snowflake(
    session: Session, df: pd.DataFrame, target_table: str, target_schema: str
):
    """Create schema if needed and save cleaned dataframe to Snowflake table."""
    session.sql(f"CREATE SCHEMA IF NOT EXISTS {target_schema}").collect()
    df_snowpark = session.create_dataframe(df)
    df_snowpark.write.mode("overwrite").save_as_table(target_table)


# ============================================================================
# Main Execution
# ============================================================================


def main() -> None:
    """Execute data cleaning pipeline."""
    settings = get_settings()
    session = create_snowpark_session(settings)

    print("=" * 80)
    print("Processing and clean Raw Tickets Data...")
    try:
        df = load_raw_data(session, CLEANING_RULES["source_table"])

        df = apply_column_filters(
            df,
            CLEANING_RULES["exclude_column_patterns"],
            CLEANING_RULES["exclude_column_name"],
        )

        df = apply_length_filters(
            df,
            CLEANING_RULES["min_body_length"],
            CLEANING_RULES["min_answer_length"],
        )

        if CLEANING_RULES["remove_duplicates"]:
            df = df.drop_duplicates(
                subset=CLEANING_RULES["duplicate_columns"]
            ).copy()
        df = df.reset_index(drop=True)
        save_to_snowflake(
            session,
            df,
            CLEANING_RULES["target_table"],
            CLEANING_RULES["target_schema"],
        )
        print("Processing and clean Raw Tickets Data finished without error !")
        print("=" * 80)

    finally:
        session.close()


if __name__ == "__main__":
    main()
