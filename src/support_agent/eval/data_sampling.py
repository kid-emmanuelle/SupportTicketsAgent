"""Data sampling functions for evaluation."""

from pathlib import Path

import pandas as pd
from snowflake.snowpark.functions import call_builtin, col, lit
from snowflake.snowpark.session import Session


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
