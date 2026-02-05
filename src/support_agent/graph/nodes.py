"""Node functions: ingest, classify, priority, retrieve, draft, guardrails, writeback."""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from ..config import Settings
from ..retrieval import retrieve_text_chunks
from .state import TicketState
from..freq_baseline.language_profiles import EN_FREQ, DE_FREQ, _letter_frequency, _cosine_similarity

def build_llm(settings: Settings) -> ChatOpenAI:
    """Build and return a ChatOpenAI instance using the provided settings."""
    # ChatOpenAI will read OPENAI_API_BASE/OPENAI_API_KEY from env by default.
    # We set them explicitly for clarity/portability.
    return ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.openai_api_base,
        api_key=settings.openai_api_key,
    )

def language_frequency_node(state: TicketState) -> dict[str, Any]:
    """Analyze letter frequency and compare against language baselines."""
    text = state["issue_description"]

    freq = _letter_frequency(text)

    sim_en = _cosine_similarity(freq, EN_FREQ)
    sim_de = _cosine_similarity(freq, DE_FREQ)

    if sim_en > sim_de:
        lang = "en"
        confidence = sim_en
    else:
        lang = "de"
        confidence = sim_de

    return {"language": lang}

def classify_topic_intent(
    llm: ChatOpenAI, state: TicketState
) -> dict[str, Any]:
    """Classify the topic and intent of a ticket using the LLM and return them as a dictionary."""
    prompt = PromptTemplate(
        input_variables=["issue_description"],
        template=open_prompt("classify.txt"),
    )
    msg = HumanMessage(
        content=prompt.format(issue_description=state["issue_description"])
    )
    raw = llm.invoke([msg]).content or ""

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
    prompt = PromptTemplate(
        input_variables=["issue_description"],
        template=open_prompt("priority.txt"),
    )
    msg = HumanMessage(
        content=prompt.format(issue_description=state["issue_description"])
    )
    raw = (llm.invoke([msg]).content or "").strip().upper()

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


def draft_response(llm: ChatOpenAI, state: TicketState) -> dict[str, Any]:
    """Draft a response to a ticket using the LLM and the retrieved context."""
    context = (
        "\n\n---\n\n".join(state.get("retrieved_context", []) or [])
        or "NO_CONTEXT_FOUND"
    )
    prompt = PromptTemplate(
        input_variables=[
            "issue_description",
            "priority_level",
            "topic",
            "intent",
            "context",
        ],
        template=open_prompt("response.txt"),
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
