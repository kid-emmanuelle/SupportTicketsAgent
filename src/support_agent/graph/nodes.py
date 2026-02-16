"""Node functions: ingest, classify, priority, retrieve, draft, guardrails, writeback."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..config import Settings
from ..freq_baseline.language_profiles import (
    DE_FREQ,
    EN_FREQ,
    _cosine_similarity,
    _letter_frequency,
)
from ..retrieval import retrieve_text_chunks
from .state import TicketState


def _get_language(state: TicketState) -> str:
    """Return ticket language, inferring from text if missing.

    Several nodes choose prompt variants based on language. Callers (including
    tests) sometimes provide only `issue_description`, so we fall back to the
    existing frequency-based detector.
    """
    lang = (state.get("language") or "").strip().lower()
    if lang in {"en", "de"}:
        return lang

    try:
        detected = language_frequency_node(state).get("language")
        return str(detected or "en").strip().lower() or "en"
    except Exception:
        return "en"


def build_llm(settings: Settings) -> ChatOpenAI:
    """Build and return a ChatOpenAI instance using the provided settings."""
    # ChatOpenAI will read OPENAI_API_BASE/OPENAI_API_KEY from env by default.
    # We set them explicitly for clarity/portability.
    return ChatOpenAI(
        model="gpt-4.1-mini",
        base_url=settings.openai_api_base,
        api_key=settings.openai_api_key,
    )


def language_frequency_node(state: TicketState) -> dict[str, Any]:
    """Analyze letter frequency and compare against language baselines."""
    text = state["issue_description"]

    freq = _letter_frequency(text)

    sim_en = _cosine_similarity(freq, EN_FREQ)
    sim_de = _cosine_similarity(freq, DE_FREQ)

    lang = "en" if sim_en > sim_de else "de"
    return {"language": lang}


def classify_topic_intent(
    llm: ChatOpenAI, state: TicketState
) -> dict[str, Any]:
    """Classify the topic and intent of a ticket using the LLM and return them as a dictionary."""
    language = _get_language(state)
    txt = "classify.txt" if language == "en" else "classify_de.txt"
    prompt = PromptTemplate(
        input_variables=["issue_description"],
        template=open_prompt(txt),
    )
    msg = HumanMessage(
        content=prompt.format(issue_description=state["issue_description"])
    )
    raw = llm.invoke([msg]).content or ""
    prompt = prompt.format(issue_description=state["issue_description"])
    # Try to parse JSON; fall back to simple defaults
    topic, intent = "other", "question"
    try:
        data = json.loads(extract_json(raw))
        topic = str(data.get("topic", topic))
        intent = str(data.get("intent", intent))
    except Exception as e:
        logging.warning(f"Failed to parse topic/intent from LLM output: {e}")

    return {"topic": topic, "intent": intent}


def evaluate_priority(llm: ChatOpenAI, state: TicketState) -> dict[str, Any]:
    """Evaluate the priority of a ticket using the LLM and return the priority level as a dictionary."""
    language = _get_language(state)
    txt = "priority.txt" if language == "en" else "priority_de.txt"
    prompt = PromptTemplate(
        input_variables=["issue_description"],
        template=open_prompt(txt),
    )
    msg = HumanMessage(
        content=prompt.format(issue_description=state["issue_description"])
    )
    raw = (llm.invoke([msg]).content or "").strip().upper()
    prompt = prompt.format(issue_description=state["issue_description"])

    if "URG" in raw:
        p = "URGENT"
    elif "HIGH" in raw:
        p = "HIGH"
    elif "MED" in raw:
        p = "MEDIUM"
    elif "LOW" in raw:
        p = "LOW"
    else:
        p = "LOW"
    return {"priority_level": p}


def retrieve_node(
    session: Any, settings: Settings, state: TicketState
) -> dict[str, Any]:
    """Retrieve relevant context for a ticket and return it as a dictionary."""
    chunks = retrieve_text_chunks(session, settings, state["issue_description"])
    return {"retrieved_context": chunks}


def retrieve_node_stub(state: TicketState) -> dict[str, Any]:
    """Fake context for testing."""
    language = _get_language(state)
    return {
        "retrieved_context": [
            "Sample documentation or prior tickets here."
            if language == "en"
            else "Beispieldokumentation oder frühere Tickets hier."
        ]
    }


def draft_response(llm: ChatOpenAI, state: TicketState) -> dict[str, Any]:
    """Draft a response to a ticket using the LLM and the retrieved context."""
    context = (
        "\n\n---\n\n".join(state.get("retrieved_context", []) or [])
        or "NO_CONTEXT_FOUND"
    )
    language = _get_language(state)
    txt = "response.txt" if language == "en" else "response_de.txt"
    prompt = PromptTemplate(
        input_variables=[
            "issue_description",
            "priority_level",
            "topic",
            "intent",
            "context",
        ],
        template=open_prompt(txt),
    )
    msg = HumanMessage(
        content=prompt.format(
            issue_description=state["issue_description"],
            priority_level=state.get("priority_level", "UNKNOWN"),
            topic=state.get("topic", "other"),
            intent=state.get("intent", "question"),
            context=context,
        )
    )
    resp = (llm.invoke([msg]).content or "").strip()
    prompt = prompt.format(issue_description=state["issue_description"])
    return {"final_response": resp}


# -------------------------
# Helpers
# -------------------------
def open_prompt(name: str) -> str:
    """Open and return the contents of a prompt file from the prompts package."""
    from importlib.resources import files

    return (files("support_agent.prompts") / name).read_text(encoding="utf-8")


def extract_json(text: str) -> str:
    """Extract a JSON object from a string, best-effort for model outputs wrapped in prose."""
    # Basic best-effort extraction for model outputs that wrap JSON in prose
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text
