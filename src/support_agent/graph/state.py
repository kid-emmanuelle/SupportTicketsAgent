from typing import TypedDict, Any
from snowflake.core import Root
from snowflake.snowpark import Session
# =========================
# State Definition
# =========================
class TicketAnalysisState(TypedDict):
    """State schema for the support ticket analysis pipeline."""
    # Input
    issue_description: str
    
    # Processing artifacts
    normalized_text: str
    language: str
    intent: str
    topic: str
    priority_level: str
    retrieved_docs: list
    draft_response: str
    final_response: str
    
    # Dependencies (injected)
    session: Session
    root: Root
    reasoning_engine: Any
    
    # Metadata
    timestamp: str
    ticket_id: str