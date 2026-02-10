import os

from dotenv import load_dotenv
import pytest

from support_agent.config import get_settings
from support_agent.graph.build import build_graph
from support_agent.snowflake_client import create_snowpark_session


load_dotenv()


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_BASE") or not os.getenv("OPENAI_API_KEY"),
    reason="E2E requires Snowflake Cortex env vars",
)
def test_e2e_agent_smoke():
    settings = get_settings()
    session = create_snowpark_session(settings)

    agent = build_graph(session=session, settings=settings)
    out = agent.invoke(
        {"issue_description": "I want a dark mode in the dashboard"}
    )

    assert out.get("priority_level") in {"LOW", "MEDIUM", "HIGH", "URGENT"}
    assert isinstance(out.get("final_response"), str)
    assert len(out.get("final_response")) > 10
