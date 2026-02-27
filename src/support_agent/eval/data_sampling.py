"""Data sampling functions for evaluation."""

from pathlib import Path

import pandas as pd
from snowflake.snowpark.functions import call_builtin, col, lit
from snowflake.snowpark.session import Session


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
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_path = prompts_dir / f"{prompt_name}.txt"

    if not prompt_path.exists():
        raise FileNotFoundError(prompt_path)

    with Path.open(prompt_path, encoding="utf-8") as f:
        return f.read()


# Load prompts at module level
BODY_REWRITE_PROMPT = load_prompt("rewrite_body")
ANSWER_REWRITE_PROMPT = load_prompt("rewrite_answer")


# ============================================================================
# DATA FETCHING
# ============================================================================


def get_tickets_data(
    session: Session, table_name: str = "PROJECT_DB.CURATED.TICKETS_CLEANED"
) -> pd.DataFrame:
    """Fetch tickets data from Snowflake."""
    return (
        session.table(table_name)
        .to_pandas()
        .rename(columns=lambda s: s.lower())
    )


# ============================================================================
# SAMPLING
# ============================================================================


def create_stratified_sample(
    df: pd.DataFrame,
    samples_per_combination: int = 5,
    stratify_columns: list[str] | None = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """Create a stratified sample from the dataset.

    Args:
        df: Input dataframe
        samples_per_combination: Number of samples per unique combination
        stratify_columns: Columns to use for stratification (default: ['type', 'priority', 'language'])
        random_state: Random seed for reproducibility

    Returns:
        Stratified sample dataframe
    """
    if stratify_columns is None:
        stratify_columns = ["type", "priority", "language"]

    # Create stratification key
    df = df.copy()
    df["stratify_key"] = df[stratify_columns].astype(str).agg("_".join, axis=1)

    # Calculate number of unique combinations
    n_combinations = df["stratify_key"].nunique()
    n_samples = samples_per_combination * n_combinations
    sample_fraction = n_samples / len(df)

    # Perform stratified sampling
    return (
        df.groupby("stratify_key", group_keys=False)
        .apply(
            lambda x: x.sample(
                n=max(1, int(len(x) * sample_fraction)),
                random_state=random_state,
            )
        )
        .drop(columns=["stratify_key"])
        .reset_index(drop=True)
    )


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

    # Convert to pandas and lowercase column names
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


# ============================================================================
# STATISTICS
# ============================================================================


def print_sample_statistics(
    df: pd.DataFrame, title: str = "SAMPLE STATISTICS"
) -> None:
    """Print statistics about the sample."""
    print("=" * 80)
    print(title)
    print("=" * 80)
    print(f"Total samples: {len(df)}")
    print("\nDistribution:")

    if "language" in df.columns:
        print("\nBy Language:")
        print(df["language"].value_counts())

    if "priority" in df.columns:
        print("\nBy Priority:")
        print(df["priority"].value_counts())

    if "type" in df.columns:
        print("\nBy Type:")
        print(df["type"].value_counts())


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
