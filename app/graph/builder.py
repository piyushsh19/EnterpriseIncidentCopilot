"""Phase 3-4: wire the Self-RAG StateGraph and attach the SQLite checkpointer."""
import sqlite3
from functools import lru_cache
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.graph.edges import after_web_search, check_answer, decide_to_generate, grade_generation
from app.graph.nodes.contextualize import contextualize
from app.graph.nodes.generate import finalize, generate, give_up
from app.graph.nodes.grade_documents import grade_documents
from app.graph.nodes.retrieve import retrieve
from app.graph.nodes.transform_query import transform_query
from app.graph.nodes.web_search import web_search
from app.graph.state import GraphState


def build_workflow() -> StateGraph:
    g = StateGraph(GraphState)
    g.add_node("contextualize", contextualize)
    g.add_node("retrieve", retrieve)
    g.add_node("grade_documents", grade_documents)
    g.add_node("transform_query", transform_query)
    g.add_node("web_search", web_search)
    g.add_node("generate", generate)
    g.add_node("check_answer", check_answer)
    g.add_node("give_up", give_up)
    g.add_node("finalize", finalize)

    g.add_edge(START, "contextualize")
    g.add_edge("contextualize", "retrieve")
    g.add_edge("retrieve", "grade_documents")
    g.add_conditional_edges("grade_documents", decide_to_generate, {
        "generate": "generate",
        "transform_query": "transform_query",
        "web_search": "web_search",
        "give_up": "give_up",
    })
    g.add_edge("transform_query", "retrieve")
    g.add_conditional_edges("web_search", after_web_search,
                            {"generate": "generate", "give_up": "give_up"})
    g.add_edge("generate", "check_answer")
    g.add_conditional_edges("check_answer", grade_generation, {
        "generate": "generate",
        "transform_query": "transform_query",
        "useful": "finalize",
        "give_up": "give_up",
    })
    g.add_edge("give_up", "finalize")
    g.add_edge("finalize", END)
    return g


@lru_cache
def get_graph():
    """Compiled graph with persistent memory. thread_id = incident_id."""
    path = Path(get_settings().checkpoint_db)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    return build_workflow().compile(checkpointer=SqliteSaver(conn))


def run_incident_query(incident_id: str, message: str) -> dict:
    from langchain_core.messages import HumanMessage

    config = {"configurable": {"thread_id": incident_id}}
    return get_graph().invoke(
        {"question": message, "messages": [HumanMessage(content=message)], "route_trace": []},
        config=config,
    )
