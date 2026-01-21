"""Load CSV data into Snowflake stage and trigger ingestion.

Optional helper script.
Normally, data loading is done via Snowsight SQL worksheet or a notebook.
But if we want to automate it from Python:
- upload CSV to a stage
- run COPY INTO
This script intentionally leaves those details to the environment constraints.
"""

from __future__ import annotations


def main():
    """Execute data loading placeholder."""
    msg = "Implement load_data. py for the environment (stage + COPY INTO)."
    raise SystemExit(msg)


if __name__ == "__main__":
    main()
