"""Phase 2-3: fetch top-k chunks from Pinecone."""
from app.graph.state import GraphState
from app.services.retry import call_upstream
from app.services.vectorstore import get_retriever


def retrieve(state: GraphState) -> dict:
    retriever = get_retriever()
    docs = call_upstream("Pinecone", lambda: retriever.invoke(state["question"]))
    return {"documents": docs, "route_trace": state.get("route_trace", []) + ["retrieve"]}
