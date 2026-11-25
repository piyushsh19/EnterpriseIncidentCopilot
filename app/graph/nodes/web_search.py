"""Phase 4: Tavily fallback when internal docs don't cover the incident."""
from langchain_core.documents import Document

from app.config import get_settings
from app.graph.state import GraphState


def web_search(state: GraphState) -> dict:
    from tavily import TavilyClient

    s = get_settings()
    trace = state.get("route_trace", []) + ["web_search"]
    try:
        results = TavilyClient(api_key=s.tavily_api_key).search(
            state["question"], max_results=s.web_results
        ).get("results", [])
    except Exception:  # TODO Phase 5: log + mark audit status "degraded"
        results = []

    docs = [
        Document(page_content=r.get("content", ""),
                 metadata={"source": r.get("url"), "title": r.get("title"), "doc_type": "web"})
        for r in results
    ]
    return {"documents": docs, "web_used": True, "route_trace": trace}
