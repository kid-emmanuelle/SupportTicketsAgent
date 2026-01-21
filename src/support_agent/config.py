"""Configuration settings for the Support Agent."""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    # Snowflake
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema: str

    # Cortex (OpenAI-compatible)
    openai_api_base: str
    openai_api_key: str
    llm_model: str

    # Cortex Search
    search_db: str
    search_schema: str
    search_service: str
    top_k: int


def get_settings() -> Settings:
    """Load settings from environment (.env supported)."""
    load_dotenv()

    def req(name: str) -> str:
        v = os.getenv(name)
        if not v:
            msg = f"Missing required env var:  {name}"
            raise RuntimeError(msg)
        return v

    return Settings(
        account=req("SNOWFLAKE_ACCOUNT"),
        user=req("SNOWFLAKE_USER"),
        password=req("SNOWFLAKE_PASSWORD"),
        role=os.getenv("SNOWFLAKE_ROLE", ""),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", ""),
        database=os.getenv("SNOWFLAKE_DATABASE", "PROJECT_DB"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", ""),
        openai_api_base=req("OPENAI_API_BASE"),
        openai_api_key=req("OPENAI_API_KEY"),
        llm_model=os.getenv("LLM_MODEL", "openai-gpt-5"),
        search_db=os.getenv(
            "CORTEX_SEARCH_DB", os.getenv("SNOWFLAKE_DATABASE", "PROJECT_DB")
        ),
        search_schema=os.getenv(
            "CORTEX_SEARCH_SCHEMA", os.getenv("SNOWFLAKE_SCHEMA", "")
        ),
        search_service=os.getenv(
            "CORTEX_SEARCH_SERVICE", "support_tickets_search_service"
        ),
        top_k=int(os.getenv("RETRIEVE_TOP_K", "8")),
    )
