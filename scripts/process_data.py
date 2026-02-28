"""Process and clean support tickets data with configurable rules.

This script:
1. Loads raw tickets from Snowflake
2. Applies configurable cleaning rules
3. Saves cleaned data to curated schema
4. Rewrites body and answer fields using Cortex
"""

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from snowflake.snowpark.functions import call_builtin, col, lit
from snowflake.snowpark.session import Session

from src.support_agent.config import get_settings
from src.support_agent.snowflake_client import create_snowpark_session


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
    "keep_column_name": ["tag_1", "tag_2"],
    # Whether to remove duplicates
    "remove_duplicates": True,
    "duplicate_columns": ["body", "answer"],
    # Source and target tables
    "source_table": "PROJECT_DB.RAW.SUPPORT_TICKETS",
    "target_schema": "PROJECT_DB.CURATED",
    "target_table": "PROJECT_DB.CURATED.TICKETS_CLEANED",
    # Rewriting configuration
    "rewrite_model": "claude-3-5-sonnet",
}


# ============================================================================
# PROMPT LOADING
# ============================================================================


def load_prompt(prompt_name: str) -> str:
    """Load prompt from text file.

    Args:
        prompt_name: Name of the prompt file (without .txt extension)

    Returns:
        Prompt content as string
    """
    prompts_dir = (
        Path(__file__).parent.parent / "src" / "support_agent" / "prompts"
    )
    prompt_path = prompts_dir / f"{prompt_name}.txt"

    if not prompt_path.exists():
        raise FileNotFoundError(prompt_path)

    with Path.open(prompt_path, encoding="utf-8") as f:
        return f.read()


# Load prompts at module level
BODY_REWRITE_PROMPT = load_prompt("rewrite_body")
ANSWER_REWRITE_PROMPT = load_prompt("rewrite_answer")


# ============================================================================
# DATA LOADING AND CLEANING FUNCTIONS
# ============================================================================


def load_data(session: Session, source_table: str) -> pd.DataFrame:
    """Load raw tickets data from Snowflake."""
    return (
        session.table(source_table)
        .to_pandas()
        .rename(columns=lambda s: s.lower())
    )


def apply_column_filters(
    df: pd.DataFrame,
    exclude_patterns: list,
    exclude_column: list,
    keep_columns: list,
) -> pd.DataFrame:
    """Remove columns matching exclude patterns."""
    cols = [
        col
        for col in df.columns
        if (col in keep_columns)
        or (
            not any(pattern in col for pattern in exclude_patterns)
            and col not in exclude_column
        )
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
    """Create schema if needed and save cleaned dataframe to Snowflake table.

    Note: Column names are converted to uppercase to match Snowflake conventions.
    """
    session.sql(f"CREATE SCHEMA IF NOT EXISTS {target_schema}").collect()

    # Convert column names to uppercase before saving
    df_upper = df.copy()
    df_upper.columns = [c.upper() for c in df_upper.columns]

    df_snowpark = session.create_dataframe(df_upper)
    df_snowpark.write.mode("overwrite").save_as_table(target_table)


# ============================================================================
# REWRITING WITH CORTEX
# ============================================================================


def rewrite_sample_data(
    session: Session, df: pd.DataFrame, model: str = "claude-3-5-sonnet"
) -> pd.DataFrame:
    """Rewrite body and answer fields using Snowflake Cortex Complete.

    Args:
        session: Snowflake session
        df: Sample dataframe with 'body' and 'answer' columns
        model: Cortex model to use

    Returns:
        Dataframe with added 'rewritten_body' and 'cleaned_answer' columns
    """
    print(f"Rewriting {len(df)} tickets using {model}...")

    # Ensure column names are uppercase before uploading
    df_upper = df.copy()
    df_upper.columns = [c.upper() for c in df_upper.columns]

    # Upload sample to temporary table
    temp_table = "PROJECT_DB.EVAL.TEMP_REWRITE_SAMPLE"
    df_snowpark = session.create_dataframe(df_upper)
    df_snowpark.write.mode("overwrite").save_as_table(temp_table)

    # Load the table back as Snowpark DataFrame
    temp_df = session.table(temp_table)

    # Use Snowpark API for safe query construction
    # Replace placeholders in prompts with actual column values
    body_prompt_with_data = call_builtin(
        "REPLACE", lit(BODY_REWRITE_PROMPT), lit("{body}"), col("BODY")
    )

    answer_prompt_with_data = call_builtin(
        "REPLACE", lit(ANSWER_REWRITE_PROMPT), lit("{answer}"), col("ANSWER")
    )

    # Call Cortex Complete using Snowpark functions
    rewritten_body = call_builtin(
        "SNOWFLAKE.CORTEX.COMPLETE", lit(model), body_prompt_with_data
    ).alias("REWRITTEN_BODY")

    cleaned_answer = call_builtin(
        "SNOWFLAKE.CORTEX.COMPLETE", lit(model), answer_prompt_with_data
    ).alias("CLEANED_ANSWER")

    # Add new columns to DataFrame
    result_snowpark = temp_df.select("*", rewritten_body, cleaned_answer)

    # Convert to pandas and lowercase column names for processing
    result_df = result_snowpark.to_pandas()
    result_df.columns = [c.lower() for c in result_df.columns]

    # Clean up prefixes from answers
    unwanted_prefixes = [
        "Here is the cleaned answer:",
        "Cleaned Answer:",
        "Cleaned:",
        "Here's the cleaned version:",
    ]

    def clean_response(text: str) -> str:
        if not isinstance(text, str):
            return text
        text = text.strip()
        for prefix in unwanted_prefixes:
            if text.startswith(prefix):
                text = text[len(prefix) :].strip()
        return text

    result_df["cleaned_answer"] = result_df["cleaned_answer"].apply(
        clean_response
    )

    # Clean up temporary table
    session.sql(f"DROP TABLE IF EXISTS {temp_table}").collect()

    print("✓ Rewriting complete!")
    return result_df


def save_rewritten_data(session: Session, df: pd.DataFrame, target_table: str):
    """Save rewritten data back to Snowflake with uppercase column names."""
    # Convert column names to uppercase
    df_upper = df.copy()
    df_upper.columns = [c.upper() for c in df_upper.columns]

    df_snowpark = session.create_dataframe(df_upper)
    df_snowpark.write.mode("overwrite").save_as_table(target_table)
    print(f"✓ Saved rewritten data to {target_table}")


def print_rewriting_samples(df: pd.DataFrame, n_samples: int = 3) -> None:
    """Print sample comparisons of original and rewritten text."""
    import textwrap

    print("=" * 80)
    print(f"REWRITING EXAMPLES (showing {n_samples} samples)")
    print("=" * 80)

    sample = df.sample(n=min(n_samples, len(df)), random_state=42)

    for i, (_idx, row) in enumerate(sample.iterrows(), 1):
        print(f"\n{'=' * 80}")
        print(f"SAMPLE {i}/{n_samples}")
        print(f"{'=' * 80}")
        print(
            f"Language: {row.get('language', 'N/A')} | Queue: {row.get('queue', 'N/A')}"
        )

        print("\nORIGINAL BODY:")
        for line in textwrap.wrap(str(row["body"]), width=76):
            print(f"  {line}")

        print("\nREWRITTEN BODY:")
        for line in textwrap.wrap(str(row["rewritten_body"]), width=76):
            print(f"  {line}")

        print("\nORIGINAL ANSWER:")
        for line in textwrap.wrap(str(row["answer"]), width=76):
            print(f"  {line}")

        print("\nCLEANED ANSWER:")
        for line in textwrap.wrap(str(row["cleaned_answer"]), width=76):
            print(f"  {line}")

        print("-" * 80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main() -> None:
    """Execute data cleaning and rewriting pipeline."""
    settings = get_settings()
    session = create_snowpark_session(settings)

    print("=" * 80)
    print("Processing and clean Raw Tickets Data...")
    try:
        df = load_data(session, CLEANING_RULES["source_table"])

        df = apply_column_filters(
            df,
            CLEANING_RULES["exclude_column_patterns"],
            CLEANING_RULES["exclude_column_name"],
            CLEANING_RULES["keep_column_name"],
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

        print("✓ Data cleaned successfully!")
        print("=" * 80)

        # Rewrite body and answer to enhance text quality
        print("\nStarting text rewriting with Cortex...")
        df_rewritten = rewrite_sample_data(
            session, df, model=CLEANING_RULES["rewrite_model"]
        )

        # Print samples to verify quality
        print_rewriting_samples(df_rewritten, n_samples=3)

        # Save rewritten data to Snowflake (with uppercase columns)
        print("\nSaving rewritten data to Snowflake...")
        save_rewritten_data(
            session, df_rewritten, CLEANING_RULES["target_table"]
        )

        print("\n" + "=" * 80)
        print("Processing and clean Raw Tickets Data finished without error !")
        print("=" * 80)

    finally:
        session.close()


if __name__ == "__main__":
    main()
