"""Graph construction and compilation."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from ..config import Settings
from .nodes import (
    build_llm,
    classify_topic_intent,
    draft_response,
    evaluate_priority,
    retrieve_node,
)
from .state import TicketState


def build_graph(*, session: object, settings: Settings) -> StateGraph:
    """Build and compile the support agent state graph using the provided session and settings.

    Args:
        session: The session or database/session object used for retrieval.
        settings: The Settings object containing configuration for the agent.

    Returns:
        A compiled StateGraph representing the agent workflow.
    """
    llm = build_llm(settings)

    graph = StateGraph(state_schema=TicketState)

    # Wrap nodes so they capture llm/session/settings
    graph.add_node("classify", lambda s: classify_topic_intent(llm, s))
    graph.add_node("priority", lambda s: evaluate_priority(llm, s))
    graph.add_node("retrieve", lambda s: retrieve_node(session, settings, s))
    graph.add_node("respond", lambda s: draft_response(llm, s))

    graph.add_edge(START, "classify")
    graph.add_edge("classify", "priority")
    graph.add_edge("priority", "retrieve")
    graph.add_edge("retrieve", "respond")
    graph.add_edge("respond", END)

    return graph.compile()
