# Load CSV data into Snowflake stage and trigger ingestion

from __future__ import annotations


"""Optional helper script.

Normally, data loading is done via Snowsight SQL worksheet or a notebook.
But if we want to automate it from Python:
- upload CSV to a stage
- run COPY INTO
This script intentionally leaves those details to the environment constraints.
"""


def main():
    raise SystemExit(
        "Implement load_data.py for the environment (stage + COPY INTO)."
    )


if __name__ == "__main__":
    main()
