# =========================
# LangGraph Support Ticket Agent (Full Pipeline)
# =========================
# Node functions: ingest, classify, priority, retrieve, draft, guardrails, writeback

import os

from datetime import datetime
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate

from langgraph.graph import StateGraph, START, END

from src.support_agent.config import get_settings
from src.support_agent.snowflake_client import create_snowpark_session, get_root
from src.support_agent.graph.state import TicketAnalysisState

from snowflake.core import Root
from snowflake.snowpark import Session


def ingest_request(state: TicketAnalysisState) -> dict:
    """
    Node 1: Normalize and prepare the incoming ticket text.
    """
    text = state.get("issue_description", "").strip()
    language = "en"
    normalized = text.lower()
    
    return {
        "normalized_text": normalized,
        "language": language,
    }

def classify(state: TicketAnalysisState) -> dict:
    """
    Node 2: Classify the ticket's topic and intent.
    
    Uses the reasoning engine to determine:
    - Topic: What the ticket is about (e.g., "Authentication", "Billing")
    - Intent: What the user wants (e.g., "Question", "Bug Report")
    """
    reasoning_engine = state["reasoning_engine"]
    text = state["normalized_text"]
    
    # TODO: Implement classification logic
    # Option 1: Use LLM-based classification
    # Option 2: Use keyword matching or embeddings
    # Option 3: Use a fine-tuned classifier
    
    intent = "None"
    topic = "None"
    
    return {
        "intent": intent,
        "topic": topic
    }

def evaluate_priority(state: TicketAnalysisState) -> dict:
    """
    Node 3: Evaluate ticket priority using the reasoning engine.
    """
    PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
    priority_prompt_path = PROMPTS_DIR / "priority.txt"
    with open(priority_prompt_path, "r") as f:
            priority_prompt_text = f.read()

    reasoning_engine = state["reasoning_engine"]

    prompt = PromptTemplate(
        input_variables=["issue_description"],
        template=priority_prompt_text
    )
   
    msg = HumanMessage(content=prompt.format(issue_description=state["issue_description"]))
    raw_priority = reasoning_engine.invoke([msg]).content.strip().upper()

    # Normalize output
    if "URG" in raw_priority:
        priority = "URGENT"
    elif "HIGH" in raw_priority:
        priority = "HIGH"
    elif "MED" in raw_priority:
        priority = "MEDIUM"
    else:
        priority = "LOW"

    state["priority_level"] = priority
    return state

def retrieve(state: TicketAnalysisState) -> dict:
    """
    Node 4: Retrieve relevant documentation using Cortex Search.
    Searches the knowledge base for information relevant to the ticket.
    """
    root = state["root"]
    normalized_text = state["normalized_text"]
    
    # TODO: Implement Cortex Search retrieval
    # Example:
    # search_service = root.databases["YOUR_DB"].schemas["YOUR_SCHEMA"].cortex_search_services["YOUR_SERVICE"]
    # results = search_service.search(query=normalized_text, columns=["content"], limit=5)
    
    retrieved_docs = []
    
    return {"retrieved_docs": retrieved_docs}


def draft_response(state: TicketAnalysisState) -> dict:
    """
    Node 5: Generate a draft response using retrieved context.
    Combines the ticket description with retrieved documentation
    to create a helpful, accurate response.
    """
    reasoning_engine = state["reasoning_engine"]
    issue = state["issue_description"]
    docs = state.get("retrieved_docs", [])
    
    # TODO: Implement response generation
    draft = "Response generation not yet implemented."
    
    return {"draft_response": draft}


def policy_guardrails(state: TicketAnalysisState) -> dict:
    """
    Node 6: Apply policy guardrails to the draft response.
    Checks for:
    - Sensitive information leakage
    - Inappropriate content
    - Policy compliance
    - Hallucination detection
    """
    draft = state["draft_response"]
    
    # TODO: Implement guardrails
    # - Check for PII exposure
    # - Verify factual accuracy against retrieved docs
    # - Apply content filters
    # - Check for policy violations
    
    # For now, pass through
    final_response = draft
    
    return {"final_response": final_response}


def write_back(state: TicketAnalysisState) -> dict:
    """
    Node 7: Write the results back to Snowflake.
    Stores the ticket analysis and response in the database
    for tracking and analytics.
    """
    session = state["session"]
    
    # TODO: Implement Snowflake writeback
    # Example:
    # session.sql("""
    #     INSERT INTO support_tickets (
    #         ticket_id, issue, priority, topic, response, timestamp
    #     ) VALUES (?, ?, ?, ?, ?, ?)
    # """).bind([
    #     state.get("ticket_id"),
    #     state["issue_description"],
    #     state["priority_level"],
    #     state["topic"],
    #     state["final_response"],
    #     state["timestamp"]
    # ]).collect()
    
    return {}

# =========================
# Graph Construction
# =========================

def create_ticket_agent() -> StateGraph:
    """
    Build and compile the LangGraph pipeline.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    graph = StateGraph(state_schema=TicketAnalysisState)
    
    # Add nodes
    graph.add_node("ingest_request", ingest_request)
    graph.add_node("classify", classify)
    graph.add_node("evaluate_priority", evaluate_priority)
    graph.add_node("retrieve", retrieve)
    graph.add_node("draft_response", draft_response)
    graph.add_node("policy_guardrails", policy_guardrails)
    graph.add_node("write_back", write_back)
    
    # Define pipeline flow
    graph.add_edge(START, "ingest_request")
    graph.add_edge("ingest_request", "classify")
    graph.add_edge("classify", "evaluate_priority")
    graph.add_edge("evaluate_priority", "retrieve")
    graph.add_edge("retrieve", "draft_response")
    graph.add_edge("draft_response", "policy_guardrails")
    graph.add_edge("policy_guardrails", "write_back")
    graph.add_edge("write_back", END)
    
    return graph.compile()


# =========================
# Main Execution
# =========================

def main():
    """
    Initialize the pipeline and process a sample ticket.
    """
    print("Initializing Support Ticket Agent...")
    
    # Setup Snowflake connection
    settings = get_settings()
    session = create_snowpark_session(settings)
    root = get_root(session)
    
    # Initialize reasoning engine
    reasoning_engine = ChatOpenAI(
        model="openai-gpt-5", 
    )
    
    # Compile the graph
    ticket_agent = create_ticket_agent()
    
    # Create initial state with dependencies injected
    initial_state: TicketAnalysisState = {
        "issue_description": "I cannot log into my dashboard and my payment failed.",
        "session": session,
        "root": root,
        "reasoning_engine": reasoning_engine,
        "ticket_id": f"TKT-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    }
    
    print("\nProcessing ticket...")
    print(f"Issue: {initial_state['issue_description']}\n")
    
    # Execute the pipeline
    result = ticket_agent.invoke(initial_state)
    
    # Display results
    print(f"Ticket ID:     {result.get('ticket_id')}")
    print(f"Priority:      {result.get('priority_level')}")
    print(f"Topic:         {result.get('topic')}")
    print(f"Intent:        {result.get('intent')}")
    print(f"Language:      {result.get('language')}")
    print(f"Timestamp:     {result.get('timestamp')}")
    print("RESPONSE:")
    print("-" * 60)
    print(result.get('final_response', 'No response generated'))
    
    # Cleanup
    session.close()


if __name__ == "__main__":
    main()