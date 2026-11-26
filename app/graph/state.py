"""Phase 3: the state that flows through every LangGraph node."""
from typing import Annotated, List, Optional, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class GraphState(TypedDict, total=False):
    question: str                 # current (possibly rewritten) query
    original_question: str        # what the user actually typed
    documents: List[Document]     # retrieved / graded / web docs
    generation: str               # latest draft answer
    web_used: bool
    rewrite_count: int
    generation_count: int
    route_trace: List[str]        # node names visited, for audit + UI
    grader_scores: dict
    rewritten_queries: List[str]  # every query transform_query produced
    web_error: Optional[str]      # set when Tavily failed (audit status 'degraded')
    messages: Annotated[List[BaseMessage], add_messages]  # chat memory
